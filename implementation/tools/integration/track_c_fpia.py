"""Hardened Track C Frozen Projection Identity Audit (FPIA) — CDR-014.

Audits ONE exact commit T (an actual history-preserving merge result) for Track C integration
acceptance. It never predicts or simulates a merge to reach PASS, never edits the frozen tools,
Frozen records or any branch, never writes to the caller's repository, and never pushes.

    python implementation/tools/integration/track_c_fpia.py --repo PATH --tree <40-hex T> \
        --register-commit <40-hex G> --cdr CDR-014 --out FILE.json [--work-dir DIR] [--keep-work]

There are no reference-SHA options: R (Track C) and V (v2) come only from the authenticated
CDR manifest. Exit codes: 0 FPIA_PASS, 1 FPIA_FAIL, 2 FPIA_NOT_RUN (including usage errors).
Output schema TRACK_C_FPIA/2: a canonical ``result`` section, its sha256, and ``run`` metadata.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from . import track_c_fpia_auth as fauth
    from . import track_c_fpia_checks as fchk
    from . import track_c_fpia_derive as fd
    from . import track_c_fpia_git as fgit
    from . import track_c_fpia_runner as frun
except ImportError:
    import track_c_fpia_auth as fauth
    import track_c_fpia_checks as fchk
    import track_c_fpia_derive as fd
    import track_c_fpia_git as fgit
    import track_c_fpia_runner as frun

SCHEMA = "TRACK_C_FPIA/2"
# The single pre-existing live-network test node (PIW ruling): listed explicitly, never
# caller-controlled, honoured only while its file is byte-identical to R's. Disclosed as a deviation.
NETWORK_NODE = "tests/test_raw_and_providers.py::test_live_sec_fetch_is_optional_and_not_stage2"
EVIDENCE_CLASSES = ("EXACT_CONDITION_REPLAY_UNMODIFIED_TOOL", "PROJECTION_REPLAY_UNMODIFIED_TOOL",
                    "GIT_OBJECT_IDENTITY")
NON_CLAIMS = [
    "not C6, C7 or C8 acceptance by the frozen tools on T (FROZEN_TOOLS_ON_T is a separate, verbatim "
    "BRANCH_FROZEN_VALIDATION evidence class and is never converted)",
    "not a Frozen PASS and not a re-statement of any Frozen record",
    "not C8 Freeze, not numeric configuration, not CAL_VERIFY, not Holdout access, not a publication grant, "
    "not Official/LIVE",
    "not canonical-merge approval (Worker Contract §D12; USER_DECISION_REQUIRED)",
    "the Frozen hashes are not claimed for T; integrated-tree digests are INTEGRATED_TREE_RAW",
    "CODE_IDENTITY_DIVERGED is reported as fact and is never normalised to SAME or PASS (CDR-014 §2); the "
    "COUNTERFACTUAL_CODE_IDENTITY_NORMALISED profile is FAIL-ONLY and never an equality claim",
    "full regression of non-Track C code is executed as a PASS conjunct but certifies no other capability",
    "a foreign capability's own Holdout or PIT behaviour that does not touch Track C is outside the "
    "projection; Track C's own Holdout/PIT tests run under collection equality",
    "grandchild processes spawned by tests are covered statically and by spawn records only "
    "(module provenance of grandchildren is not traced)",
    "no numeric threshold, default or tolerance is introduced; all comparisons are exact",
]
LATENT_POLICY_NOTES = [
    "L1 shared-overlay conflicts or unauthorized resolutions FAIL (fail-closed; not relaxed)",
    "L2 modification of any path existing at R by another capability FAILS (fail-closed; not relaxed)",
    "L3 unauthenticated foreign importers of Track C are FOUND (fail-closed; not relaxed)",
    "L4 any Track C/v2 head beyond the CDR manifest is FAIL/NOT_RUN until a new user-verbatim manifest names it",
    "L5 any Frozen replay that does not reproduce byte-for-byte is NOT_PRESERVED; no normalisation",
]
DEFAULT_OPTIONS = {"authority_remote": fauth.AUTHORITY_REMOTE, "require_clean_verifier": True,
                   "static_layer": True, "pytest_config_pinning": True, "plugin_autoload_disabled": True,
                   "installed_versions": None, "max_workers": None, "lanes": None}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


# ---- status composition (AC-37; review MEDIUM decision table) --------------------------------------
CONJUNCTS = ("authority", "runtime_provenance", "historical_frozen_identity", "track_c_projection",
             "integration_interference", "v2_binding", "full_regression")
FAILING = {"FAIL", "HISTORICAL_FROZEN_IDENTITY_NOT_PRESERVED", "TRACK_C_PROJECTION_NOT_PRESERVED",
           "INTEGRATION_INTERFERENCE_FOUND"}
PASSING = {"PASS", "HISTORICAL_FROZEN_IDENTITY_PRESERVED", "TRACK_C_PROJECTION_PRESERVED",
           "INTEGRATION_INTERFERENCE_NONE", "NOT_APPLICABLE"}


def compose(status):
    """Pure decision table. Returns (fpia_status, reasons)."""
    a = status.get("authority", "NOT_RUN")
    if a == "FAIL":
        return "FPIA_FAIL", ["authority FAIL (short-circuit)"]
    if a != "PASS":
        return "FPIA_NOT_RUN", ["authority %s (short-circuit)" % a]
    reasons_fail, reasons_nr = [], []
    for c in CONJUNCTS[1:]:
        v = status.get(c, "NOT_RUN")
        if v in FAILING:
            reasons_fail.append("%s %s" % (c, v))
        elif v not in PASSING:
            reasons_nr.append("%s %s" % (c, v))
    ci = status.get("code_identity", "NOT_RUN")
    if ci not in ("CODE_IDENTITY_SAME", "CODE_IDENTITY_DIVERGED"):
        reasons_nr.append("code_identity %s (must be determinate)" % ci)
    ft = status.get("frozen_tools_on_T", "NOT_RUN")
    if ft not in ("FROZEN_TOOLS_ON_T_PASS", "FROZEN_TOOLS_ON_T_FAIL"):
        reasons_nr.append("frozen_tools_on_T %s (must have run)" % ft)
    if reasons_fail:
        return "FPIA_FAIL", reasons_fail + reasons_nr
    if reasons_nr:
        return "FPIA_NOT_RUN", reasons_nr
    return "FPIA_PASS", []


def summary_line(result):
    st = result["statuses"]
    ci = result.get("code_identity", {})
    vals = ci.get("site_values", {})
    pairs = []
    for site, v in sorted(vals.items()):
        pairs.append("%s R %s -> T %s" % (site.split(":")[-1], str(v.get("R"))[:8], str(v.get("T"))[:8]))
    return " | ".join([result["fpia"]["status"],
                       "%s (%s)" % (st.get("code_identity"), "; ".join(pairs)),
                       "%s [BRANCH_FROZEN_VALIDATION, verbatim]" % st.get("frozen_tools_on_T"),
                       str(st.get("historical_frozen_identity")), str(st.get("track_c_projection")),
                       str(st.get("integration_interference")),
                       "v2_binding %s" % st.get("v2_binding"), "full_regression %s" % st.get("full_regression")])


# ---- the audit ----------------------------------------------------------------------------------------
class Audit:
    def __init__(self, repo, tree, register_commit, cdr, work, options):
        self.repo = str(Path(repo).resolve())
        self.tree_arg, self.register_arg, self.cdr = tree, register_commit, cdr
        self.work = Path(work)
        self.opts = dict(DEFAULT_OPTIONS, **(options or {}))
        unknown = sorted(set(self.opts) - set(DEFAULT_OPTIONS))
        if unknown:
            raise ValueError("unknown FPIA options: %s" % unknown)
        self.sb = fgit.Sandbox(self.work / "sandbox")
        self.runner = frun.Runner(self.work / "exec", autoload_disabled=self.opts["plugin_autoload_disabled"])
        self.result = {"schema": SCHEMA, "statuses": {}, "checks": {}, "equality_claims": [],
                       "non_claims": NON_CLAIMS, "latent_policy_notes": LATENT_POLICY_NOTES,
                       "ordering_note": fchk.overlay_ordering_note()}
        self.st = self.result["statuses"]
        self.lanes = {}

    # -- inputs ----------------------------------------------------------------------------------
    def resolve(self, value, label):
        if fgit.HEX40.match(value or ""):
            return value
        refs = self.sb.ls_remote(self.repo, value)
        hits = sorted(set(refs.values()))
        if len(hits) != 1:
            raise fgit.GitError("cannot resolve %s %r in --repo" % (label, value))
        return hits[0]

    def populate(self, shas):
        specs = ["+refs/heads/*:refs/fpia/src/heads/*", "+refs/remotes/*:refs/fpia/src/remotes/*",
                 "+refs/tags/*:refs/fpia/src/tags/*"]
        specs += ["%s:refs/fpia/in/%s" % (s, s) for s in shas]
        self.sb.fetch(self.repo, specs, label="caller-repo")

    def fetch_refs(self, shas):
        missing = [s for s in shas if not self.sb.has_commit(s)]
        if missing:
            self.sb.fetch(self.repo, ["%s:refs/fpia/in/%s" % (s, s) for s in missing], label="references")

    # -- main --------------------------------------------------------------------------------------
    def run(self):
        r = self.result
        try:
            T = self.resolve(self.tree_arg, "--tree")
            G = self.resolve(self.register_arg, "--register-commit")
            self.populate([T, G])
        except fgit.GitError as exc:
            self.st["authority"] = "NOT_RUN"
            r["authority"] = {"status": "NOT_RUN", "checks": [{"id": "AC-01", "status": "NOT_RUN",
                                                               "detail": "inputs unavailable: %s" % str(exc)[-400:]}]}
            return self.finish()
        self.T, self.G = T, G
        r["subject"] = {"tree": T, "tree_object": self.sb.tree_id(T)}
        r["merge_result_audited"] = T
        auth = fauth.authenticate(self.sb, G, self.cdr, self.fetch_refs, self.opts["authority_remote"])
        r["authority"] = dict(auth)
        if auth["status"] != "PASS":
            self.st["authority"] = auth["status"]
            return self.finish()
        self.R, self.Vs = auth["R"], auth["Vs"]
        try:
            self.derive()
        except fd.ShapeError as exc:
            r["derivation_error"] = str(exc)
            self.st["authority"] = "NOT_RUN"
            r["authority"]["checks"].append({"id": "AC-11/AC-14", "status": "NOT_RUN",
                                             "detail": "derivation shape error: %s" % exc})
            r["authority"]["status"] = "NOT_RUN"
            return self.finish()
        ref_status = self.reference_checks()
        r["authority"]["status"] = ref_status
        self.st["authority"] = ref_status
        if ref_status != "PASS":
            return self.finish()
        self.pi, self.vs = None, [V for V in self.Vs if self.v_applies.get(V)]
        self.static_phase()
        self.runtime_phase()
        if self.st.get("runtime_provenance") == "PASS" or self.st.get("runtime_provenance") is None:
            self.dynamic_phase()
        else:
            for k in ("historical_frozen_identity", "code_identity", "frozen_tools_on_T", "full_regression"):
                self.st.setdefault(k, "NOT_RUN")
        self.compose_components()
        return self.finish()

    # -- derivation ----------------------------------------------------------------------------------
    def derive(self):
        sb, R, T = self.sb, self.R, self.T
        tR = sb.tree(R)
        d = self.result.setdefault("derivation", {})
        wf_text = sb.read(R, fd.TRACK_C_WORKFLOW)
        if wf_text is None:
            raise fd.ShapeError("Track C workflow missing at R")
        self.wf_R = self.workflow(R)
        tool_paths = sorted(p for p in tR if fd.glob_match(p, fd.TOOL_GLOB))
        invoked = [s["script_path"] for s in self.wf_R["steps"] if s["kind"] == "tool"]
        missing = [p for p in invoked if p not in tR]
        if missing:
            raise fd.ShapeError("workflow invokes tools absent at R: %s" % missing)
        universe = sorted(set(tool_paths) | set(invoked))
        self.tools = {p: fd.ToolModel(p, sb.blob(tR[p].sha)) for p in universe}
        unbound_invocation = [p for p in universe if p not in invoked]
        if unbound_invocation:
            raise fd.ShapeError("Frozen tool present but not invoked by the Track C workflow: %s" % unbound_invocation)
        by_kind = {}
        for t in self.tools.values():
            by_kind.setdefault(t.kind, []).append(t)
        if any(len(v) != 1 for v in by_kind.values()):
            raise fd.ShapeError("ambiguous tool bindings")
        self.by_kind = {k: v[0] for k, v in by_kind.items()}
        c6 = self.by_kind.get("C6")
        if c6 is None:
            raise fd.ShapeError("no C6-kind tool at R")
        self.K = c6.consts["CANONICAL"]
        self.BRANCH = c6.consts["BRANCH"]
        anchors = {}
        for t in self.tools.values():
            for name, value in t.hex_constants.items():
                anchors.setdefault(value, set()).add("%s:%s" % (t.path.rsplit("/", 1)[-1], name))
        self.anchor_values = sorted(anchors)
        try:
            self.fetch_refs(self.anchor_values)
        except fgit.GitError:
            pass
        anchor_paths = {}
        for v in self.anchor_values:
            if not sb.has_commit(v):
                raise fd.ShapeError("tool anchor %s is not a commit in the sandbox" % v)
            anchor_paths[v] = set(sb.tree(v))
        self.proj = fchk.Projection(sb, R, self.tools, anchor_paths)
        if self.proj.unclassified:
            raise fd.ShapeError("unclassifiable projection paths: %s" % sorted(set(self.proj.unclassified))[:10])
        self.v_applies = {V: sb.is_ancestor(V, T) for V in self.Vs}
        self.tcm_R = fchk.track_c_modules(tR, self.proj.ns) | {"investment_system.evl"}
        self.av = set()
        self.av_reasons = {}
        for V in self.Vs:
            av, reasons = fchk.derive_av(sb, R, V, self.proj, self.tcm_R)
            self.av |= av
            self.av_reasons.update(reasons)
        self.wf_T = self.workflow(T) if sb.read(T, fd.TRACK_C_WORKFLOW) is not None else None
        # Frozen universe (records, logs, approvals) and code identity sites
        self.universe()
        self.sites = []
        for p in sorted(tR):
            if self.proj.ns(p) and p.endswith(".py") and tR[p].type == "blob" and p not in self.tools:
                for kind, name in fd.code_identity_sites(sb.blob(tR[p].sha), p):
                    self.sites.append({"path": p, "module": self.module_name(p), "kind": kind, "name": name,
                                       "root": fd.site_root(sb.blob(tR[p].sha), p)})
        for s in self.sites:
            s["importers"] = []
            for p in sorted(set(tR) | self.av):
                if not p.endswith(".py") or not (self.proj.ns(p) or p in self.av):
                    continue
                tree = tR if p in tR else sb.tree(self.Vs[0])
                if p not in tree:
                    continue
                for local, orig in fd.site_importers(sb.blob(tree[p].sha), p, fd.STATIC_ROOTS, s["module"], {s["name"]}):
                    s["importers"].append([self.module_name(p), local])
        d.update({
            "tools": [dict(t.summary(), blob=tR[t.path].sha) for t in self.tools.values()],
            "anchors": {"K": self.K, "BRANCH": self.BRANCH, "constants": {v: sorted(n) for v, n in anchors.items()}},
            "ns": {"prefixes": sorted(set().union(*[t.admit_prefixes for t in self.tools.values()]) | c6.frozen.prefixes),
                   "literals": sorted(set().union(*[t.admit_literals for t in self.tools.values()]))},
            "projection": {"counts": self.proj.counts(),
                           "overlays": {"NS_OVERLAY": self.proj.of("NS_OVERLAY"),
                                        "SHARED_OVERLAY": self.proj.of("SHARED_OVERLAY"),
                                        "INFRA_REPLACE": self.proj.of("INFRA_REPLACE"),
                                        "FROZEN_TOOL": self.proj.of("FROZEN_TOOL")},
                           "A_V": [{"path": p, "reason": self.av_reasons.get(p),
                                    "blob": self.sb.tree(self.Vs[0])[p].sha if self.Vs and p in self.sb.tree(self.Vs[0]) else None}
                                   for p in sorted(self.av)]},
            "v_applies": self.v_applies,
            "code_identity_sites": [{k: v for k, v in s.items()} for s in self.sites],
        })

    def module_name(self, p):
        for root in ("implementation/src", "implementation"):
            dname = fd.dotted(p, root)
            if dname:
                return dname
        return None

    def workflow(self, X):
        text = self.sb.read(X, fd.TRACK_C_WORKFLOW).decode("utf-8", "replace")
        wf = fd.parse_workflow(text)
        steps = []
        for st in wf["steps"]:
            kind, env, rest = fd.classify_step(st["run"])
            wd = st["wd"] or wf["defaults_wd"] or ""
            step = {"name": st["name"], "run": st["run"], "kind": kind, "env": env, "wd": wd}
            if kind == "tool":
                script = rest[0]
                step["script"] = script
                step["script_path"] = (wd.rstrip("/") + "/" + script) if wd else script
                step["args"] = rest[1:]
            elif kind == "pytest":
                step["args"] = rest
            elif kind == "pip":
                step["pins"] = fd.pins_from(rest)
            steps.append(step)
        return {"name": wf["name"], "jobs": wf["jobs"], "python_version": wf["python_version"], "steps": steps,
                "blob": fgit.blob_id(text.encode())}

    # -- Frozen universe (AC-11 + review HIGH #1) --------------------------------------------------------
    def universe(self):
        sb, R = self.sb, self.R
        tR = sb.tree(R)
        recs, logs, unbound = [], [], []
        record_paths = sorted(p for p in tR if fd.glob_match(p, fd.RECORD_GLOB))
        for V in self.Vs:
            if self.v_applies.get(V):
                record_paths += sorted(p for p in sb.tree(V) if fd.glob_match(p, fd.RECORD_GLOB) and p not in tR)
        log_paths = sorted(p for p in tR if fd.glob_match(p, fd.CI_LOG_GLOB))
        evidence_logs = {}
        for p in log_paths:
            lines = []
            for i, raw in enumerate(sb.read(R, p).split(b"\n")):
                text = raw.decode("utf-8", "replace").rstrip("\r")
                if "_EVIDENCE=" not in text or "TRACK_C_" not in text:
                    continue
                m = fd.EVIDENCE_LINE_RE.match(text)
                if not m:
                    unbound.append({"path": p, "line": i + 1, "problem": "evidence line not parseable"})
                    continue
                try:
                    obj = json.loads(m.group(3))
                except ValueError:
                    unbound.append({"path": p, "line": i + 1, "problem": "evidence JSON invalid"})
                    continue
                head = fd.evidence_head(obj)
                if head is None:
                    unbound.append({"path": p, "line": i + 1, "problem": "evidence head undeterminable"})
                    continue
                lines.append({"path": p, "line": i + 1, "prefix": m.group(2), "head": head,
                              "body": m.group(2) + "=" + m.group(3)})
            if lines:
                evidence_logs[p] = lines
                logs.extend(lines)
        log_basenames = {p.rsplit("/", 1)[-1]: p for p in evidence_logs}
        for p in record_paths:
            tree = tR if p in tR else sb.tree(next(V for V in self.Vs if self.v_applies.get(V) and p in sb.tree(V)))
            try:
                rec = json.loads(sb.blob(tree[p].sha))
            except ValueError:
                unbound.append({"path": p, "problem": "record JSON invalid"})
                continue
            cands = fd.evidence_candidates(rec) if isinstance(rec, (dict, list)) else []
            refs_log = sorted({log_basenames[v.rsplit("/", 1)[-1]] for v in fd.scalar_values(rec)
                               if isinstance(v, str) and v.rsplit("/", 1)[-1] in log_basenames})
            if not cands and not refs_log:
                continue
            entry = {"path": p, "blob": tree[p].sha, "embedded": [], "logs": refs_log}
            for path, obj in cands:
                head = fd.evidence_head(obj)
                if head is None:
                    unbound.append({"path": p, "problem": "embedded evidence head undeterminable",
                                    "at": "/".join(map(str, path))})
                    continue
                entry["embedded"].append({"at": list(path), "head": head, "keys": sorted(obj)})
            if not cands:
                heads = [k for k, v in rec.items() if "head" in k and isinstance(v, str) and fd.HEX40.match(v)]
                if len(heads) != 1:
                    unbound.append({"path": p, "problem": "log-referencing record without a unique head field"})
                    continue
                entry["head_field"] = heads[0]
                entry["head"] = rec[heads[0]]
            recs.append(entry)
        # approvals referenced by Track C code (review HIGH #1 iii)
        approvals = []
        for p in sorted(tR):
            if not (p.endswith(".py") and self.proj.ns(p)) or p in self.tools:
                continue
            paths, pins = fd.file_relative_paths(sb.blob(tR[p].sha), p)
            for q in paths:
                if q.endswith(".json") and "approval" in q.rsplit("/", 1)[-1].lower():
                    e = tR.get(q)
                    approvals.append({"path": q, "referenced_by": p, "blob_R": e.sha if e else None,
                                      "code_pinned": bool(e and e.sha in pins)})
        heads = sorted({x["head"] for x in logs} | {e["head"] for r in recs for e in r["embedded"]}
                       | {r["head"] for r in recs if "head" in r})
        self.frozen = {"records": recs, "logs": logs, "approvals": approvals, "unbound": unbound, "heads": heads}
        self.result.setdefault("derivation", {})["frozen_universe"] = {
            "tools": sorted(self.tools), "records": [{k: v for k, v in r.items()} for r in recs],
            "evidence_lines": [{k: v for k, v in x.items() if k != "body"} | {"sha256": sha256(x["body"].encode())}
                               for x in logs],
            "approvals": approvals, "unbound": unbound, "replay_heads": heads}

    # -- reference checks (AC-04, AC-07, approval consistency) -------------------------------------------
    def reference_checks(self):
        sb, R, T = self.sb, self.R, self.T
        checks = self.result["authority"]["checks"]

        def add(cid, status, detail, **extra):
            checks.append(dict({"id": cid, "status": status, "detail": detail}, **extra))

        status = "PASS"
        if not sb.is_ancestor(R, T):
            add("AC-04", "FAIL", "R is not an ancestor of T (squash or non-merge-preserving landing)")
            status = "FAIL"
        for V in self.Vs:
            if not sb.is_ancestor(R, V):
                add("AC-04", "FAIL", "authenticated V is not a descendant of R", V=V)
                status = "FAIL"
        for v in self.anchor_values:
            if not sb.is_ancestor(v, R):
                add("AC-04", "FAIL", "tool anchor is not an ancestor of R", anchor=v)
                status = "FAIL"
        for h in self.frozen["heads"]:
            try:
                self.fetch_refs([h])
            except fgit.GitError:
                pass
            if not sb.has_commit(h) or not sb.is_ancestor(h, R):
                add("AC-04", "FAIL", "Frozen evidence head is not an ancestor of R", head=h)
                status = "FAIL"
        c8 = self.by_kind.get("C8_PARTIAL")
        for a in self.frozen["approvals"]:
            if a["blob_R"] is None:
                add("AC-11", "NOT_RUN", "approval referenced by Track C code is absent at R", path=a["path"])
                status = "NOT_RUN" if status == "PASS" else status
                continue
            if not a["code_pinned"]:
                add("AC-11", "NOT_RUN", "approval referenced by Track C code is not blob-pinned in that code",
                    path=a["path"])
                status = "NOT_RUN" if status == "PASS" else status
                continue
            rec = json.loads(sb.blob(a["blob_R"]))
            if isinstance(rec, dict):
                if "canonical_head" in rec and rec["canonical_head"] != self.K:
                    add("AC-04", "FAIL", "approval canonical_head differs from the C6 CANONICAL", path=a["path"])
                    status = "FAIL"
                if c8 is not None and "baseline_head" in rec and rec["baseline_head"] != c8.consts.get("BASE"):
                    add("AC-04", "FAIL", "approval baseline_head differs from the C8 BASE", path=a["path"])
                    status = "FAIL"
        if self.frozen["unbound"]:
            add("AC-11", "NOT_RUN", "unbound Frozen evidence items", items=self.frozen["unbound"][:10])
            status = "NOT_RUN" if status == "PASS" else status
        # AC-07 tool lineage at each Frozen evidence head
        tR = sb.tree(R)
        for h in self.frozen["heads"]:
            if not sb.has_commit(h) or not sb.is_ancestor(h, R):
                continue
            tE = sb.tree(h)
            for path, model in self.tools.items():
                if path not in tE:
                    continue
                try:
                    old = fd.ToolModel(path, sb.blob(tE[path].sha))
                except fd.ShapeError as exc:
                    add("AC-07", "NOT_RUN", "tool at evidence head not bindable: %s" % exc, head=h, tool=path)
                    status = "NOT_RUN" if status == "PASS" else status
                    continue
                if old.kind != model.kind or old.hex_constants != model.hex_constants or old.branch != model.branch:
                    add("AC-07", "FAIL", "tool constants changed since the evidence head", head=h, tool=path)
                    status = "FAIL"
                if old.allowed != model.allowed or old.append_only != model.append_only:
                    add("AC-07", "FAIL", "tool modification allowlist changed since the evidence head", head=h, tool=path)
                    status = "FAIL"
                if old.admit_prefixes != model.admit_prefixes or old.frozen.prefixes != model.frozen.prefixes:
                    add("AC-07", "FAIL", "admitted-new or protection prefixes changed since the evidence head",
                        head=h, tool=path)
                    status = "FAIL"
                for lit in sorted(model.admit_literals - old.admit_literals):
                    if lit not in tR or lit in tE:
                        add("AC-07", "FAIL", "admitted literal is not a path added on the R lineage after the head",
                            head=h, tool=path, literal=lit)
                        status = "FAIL"
        if status == "PASS":
            add("AC-04/AC-07", "PASS", "ancestry, anchors, approvals and tool lineage verified")
        return status

    # -- static phase --------------------------------------------------------------------------------
    def static_phase(self):
        sb, R, T = self.sb, self.R, self.T
        r = self.result
        pchecks, v2checks, changed = fchk.projection_identity(sb, R, self.Vs, T, self.proj, self.av, self.v_applies)
        self.projection_checks = pchecks
        self.v2_checks = v2checks
        r["track_c_projection"] = {"changed_paths": changed, "checks": pchecks}
        # provenance
        vs = [V for V in self.Vs if self.v_applies.get(V)]
        L = vs[0] if vs else R
        protected = (set(sb.tree(R)) - set(self.proj.of("SHARED_OVERLAY"))) | self.av
        prov, info = fchk.provenance(sb, T, L, protected, self.proj.of("SHARED_OVERLAY"))
        if len(vs) > 1:
            for V in vs[1:]:
                p2, _ = fchk.provenance(sb, T, V, protected, self.proj.of("SHARED_OVERLAY"))
                prov += p2
        self.provenance_checks = prov
        r["track_c_projection"]["provenance"] = dict(info, checks=prov,
                                                     git_log_literal_diagnostic=fchk.git_log_diagnostic(sb, T, L, protected))
        # DR linkage (review LOW)
        dr = self.proj.of("NS_OVERLAY")
        linkage = []
        for p in dr:
            tT = sb.tree(T)
            for V in vs:
                if tT.get(p) is not None and tT[p] == sb.tree(V).get(p) and tT[p] != sb.tree(R)[p]:
                    reg_dir = fauth.REGISTER_PATH.rsplit("/", 1)[0]
                    linkage.append(dict(fauth.dr_linkage(sb, R, V, self.G, p, reg_dir), path=p, V=V,
                                        cdr_manifest={"register_blob": r["authority"].get("register_blob"),
                                                      "section_sha256": r["authority"].get("section_sha256"),
                                                      "manifest_line": r["authority"].get("manifest_line")}))
        self.dr_linkage = linkage
        r["track_c_projection"]["decision_register_linkage"] = linkage
        # complement static checks
        if self.wf_T is None:
            config_dirs = {"", "implementation", "implementation/tests"}
        else:
            config_dirs = {"", "implementation"}
            for st in self.wf_T["steps"]:
                if st["kind"] == "pytest":
                    for a in st["args"]:
                        if not a.startswith("-"):
                            parts = (st["wd"].rstrip("/") + "/" + a).split("/")[:-1]
                            for i in range(len(parts) + 1):
                                config_dirs.add("/".join(parts[:i]))
        try:
            self.config_names = fchk.config_names_from_pytest()
        except fd.ShapeError as exc:
            self.config_names = None
            r["config_names_error"] = str(exc)
        tcm_all = set(self.tcm_R)
        for p in self.av:
            for root in fd.STATIC_ROOTS:
                dname = fd.dotted(p, root)
                if dname:
                    tcm_all.add(dname)
        self.tcm_all = tcm_all
        comp, findings = fchk.complement_static(sb, T, R, self.Vs, self.v_applies, self.proj,
                                                {p for p in self.av if any(self.v_applies.get(V) for V in self.Vs)},
                                                tcm_all, self.config_names or [], config_dirs,
                                                fd.TRACK_C_WORKFLOW, None)
        self.complement = set(comp)
        orders = [("tools", list(fd.STATIC_ROOTS)), ("pytest", ["implementation", "implementation/src"])]
        closure, checked = fchk.closure_identity(sb, T, R, self.Vs, self.v_applies, self.proj, self.av, orders)
        attr_findings, attr_info = fchk.gitattributes_check(sb, R, T, sorted(sb.tree(R)))
        av_attr = []
        for V in self.Vs:
            if self.v_applies.get(V):
                f2, _ = fchk.gitattributes_check(sb, V, T, sorted(p for p in self.av if p in sb.tree(V)))
                av_attr += f2
        static = findings + closure + attr_findings + av_attr
        if not self.opts["static_layer"]:
            r["static_layer"] = {"disabled_for_test": True, "would_have_found": static}
            static = []
        self.static_findings = static
        r["integration_interference"] = {"complement_count": len(comp), "static_findings": static,
                                         "closure_names_checked": checked, "gitattributes": attr_info,
                                         "config_names": self.config_names, "config_dirs": sorted(config_dirs)}

    # -- runtime provenance (AC-36, AC-29, review LOW) ---------------------------------------------------
    def runtime_phase(self):
        r = self.result
        checks = []
        pins = {}
        pyver = None
        if self.wf_T:
            for st in self.wf_T["steps"]:
                if st["kind"] == "pip":
                    pins.update(st["pins"])
            pyver = self.wf_T["python_version"]
        installed = self.opts["installed_versions"] or {"python": "%d.%d" % sys.version_info[:2],
                                                         **frun.distributions()}
        status = "PASS"
        if pyver is not None and installed.get("python") != pyver:
            checks.append({"id": "AC-36", "status": "NOT_RUN", "detail": "python version differs from the workflow pin",
                           "pin": pyver, "actual": installed.get("python")})
            status = "NOT_RUN"
        for name, ver in sorted(pins.items()):
            actual = installed.get(name)
            if actual is None or (ver is not None and actual != ver):
                checks.append({"id": "AC-36", "status": "NOT_RUN", "detail": "distribution differs from the workflow pin",
                               "dist": name, "pin": ver, "actual": actual})
                status = "NOT_RUN"
        problems, hooks = frun.verify_site_packages()
        if problems:
            checks.append({"id": "AC-36", "status": "NOT_RUN", "detail": "installed files do not match RECORD hashes "
                           "or unlisted startup hooks", "problems": problems[:20]})
            status = "NOT_RUN"
        feats = self.sb.feature_probe()
        for f in ("merge-tree --write-tree", "check-attr --source"):
            if not feats.get(f):
                checks.append({"id": "AC-36", "status": "NOT_RUN", "detail": "git feature missing: " + f})
                status = "NOT_RUN"
        verifier = self.verifier()
        if self.opts["require_clean_verifier"] and not verifier.get("clean"):
            checks.append({"id": "AC-36", "status": "NOT_RUN", "detail": "FPIA verifier files are not a clean "
                           "committed checkout", "verifier": verifier})
            status = "NOT_RUN"
        anc = []
        p = self.work.resolve()
        for d in [p, *p.parents]:
            for n in (self.config_names or []) + ["setup.py", "conftest.py"]:
                if (d / n).is_file():
                    anc.append(str(d / n))
        if anc:
            checks.append({"id": "AC-27", "status": "FAIL", "detail": "pytest configuration in an ancestor of the "
                           "work directory", "files": anc})
            status = "FAIL"
        if self.config_names is None:
            checks.append({"id": "AC-27", "status": "NOT_RUN", "detail": "installed pytest config names not derivable"})
            status = "NOT_RUN" if status == "PASS" else status
        base = self.runner.hardened("baseline", self.work, self.work, "baseline", [])
        self.baseline_meta = (base.trace or {}).get("meta_path", [])
        flags = (base.trace or {}).get("flags", {})
        if base.rc != 0 or not all(flags.get(k) for k in ("isolated", "ignore_environment", "no_user_site",
                                                          "dont_write_bytecode")):
            checks.append({"id": "AC-29", "status": "NOT_RUN", "detail": "hardened launcher baseline failed",
                           "rc": base.rc, "flags": flags})
            status = "NOT_RUN"
        self.st["runtime_provenance"] = status
        r["runtime_provenance"] = {
            "status": status, "checks": checks, "python": {"version": sys.version, "implementation": platform.python_implementation(),
                                                           "executable_sha256": frun.sha256_file(os.path.realpath(sys.executable))},
            "required_pins": {"source_path": fd.TRACK_C_WORKFLOW, "source_blob": self.wf_T["blob"] if self.wf_T else None,
                              "python": pyver, "pins": pins},
            "installed": installed, "site_startup_hooks": hooks, "git": feats,
            "launcher_sha256": self.runner.launcher_sha256, "counterfactual_module_sha256": self.runner.counterfactual_sha256,
            "env_whitelist": sorted(self.runner.env(Path("/x")).keys()), "ignored_parent_env": frun.ignored_parent_env(),
            "baseline_meta_path": self.baseline_meta, "verifier": verifier,
            "network": {"authority_remote_fetch_only": True}}

    def verifier(self):
        return verifier_provenance(frun.HERE, self.work)

    # -- dynamic phase ---------------------------------------------------------------------------------
    def lane_dir(self, name):
        return self.work / "trees" / name

    def materialise(self, name, commit, refs):
        dest = self.lane_dir(name)
        entries = self.sb.materialise(commit, dest, refs=refs, purpose=name)
        return dest, entries

    def pytest_args(self, root, step_args, rootdir_rel, extra=()):
        empty = self.work / "pytest-empty.ini"
        if not empty.exists():
            empty.write_text("[pytest]\n")
        args = list(step_args)
        if self.opts["pytest_config_pinning"]:
            rd = str(root / rootdir_rel) if rootdir_rel else str(root)
            args += ["-c", str(empty), "--rootdir", rd, "--confcutdir", rd]
        args += ["-p", "no:cacheprovider"] + list(extra)
        return args

    def determine_rootdir(self, root, wd, files):
        from _pytest.config import findpaths
        inv = root / wd if wd else root
        rootdir, inipath, _cfg, _ignored = findpaths.determine_setup(
            inifile=None, override_ini=None, args=[str(inv / f) for f in files] or [str(inv)],
            rootdir_cmd_arg=None, invocation_dir=inv)
        rel = os.path.relpath(str(rootdir), str(root))
        return ("" if rel == "." else rel), (os.path.relpath(str(inipath), str(root)) if inipath else None)

    def pytest_session(self, lane, label, root, entries, wd, files, extra=(), track_c=True, audit=True, sites=()):
        rootdir_rel, inipath = self.determine_rootdir(root, wd, files)
        junit = self.runner.work / "junit" / (label.replace("/", "_") + ".xml")
        junit.parent.mkdir(parents=True, exist_ok=True)
        args = self.pytest_args(root, ["-q", *files], rootdir_rel, extra) + ["--junitxml", str(junit)]
        sys_path = [str(root / wd), str(root / wd / "src")] if wd else [str(root), str(root / "src")]
        res = self.runner.hardened(label, root, root / wd, "pytest", sys_path, {"args": args},
                                   pythonpath="src", audit=audit, sites=sites)
        rec = (res.trace or {}).get("pytest", {})
        prefix = (rootdir_rel + "/") if rootdir_rel else ""
        norm = lambda n: prefix + n  # noqa: E731
        reports = {norm(k): v for k, v in rec.get("reports", {}).items()}
        out = {"label": label, "rc": res.rc, "rootdir": rootdir_rel, "inifile": inipath, "files": list(files),
               "collected": sorted(norm(n) for n in rec.get("collected", [])),
               "deselected": sorted(norm(n) for n in rec.get("deselected", [])),
               "collect_errors": rec.get("collect_errors", []),
               "outcomes": frun.node_outcomes(reports), "recorder_counts": frun.recorder_counts(reports),
               "junit": frun.junit_counts(junit), "plugins": rec.get("plugins", []),
               "pytest_file": rec.get("pytest_file"), "result": res, "root": str(root)}
        return out

    def plugin_findings(self, session, root):
        out = []
        pytest_dir = os.path.dirname(os.path.dirname(session.get("pytest_file") or "")) if session.get("pytest_file") else None
        for p in session.get("plugins", []):
            if p.get("fpia"):
                continue
            f = p.get("file")
            if f is None:
                continue
            real = os.path.realpath(f)
            if pytest_dir and (real.startswith(os.path.join(pytest_dir, "_pytest") + "/")
                               or real.startswith(os.path.join(pytest_dir, "pytest") + "/")
                               or real.startswith(os.path.join(pytest_dir, "pluggy") + "/")):
                continue
            rr = os.path.realpath(str(root)) + "/"
            if real.startswith(rr):
                rel = real[len(rr):]
                if rel.rsplit("/", 1)[-1] == "conftest.py" and rel in self.sb.tree(self.R):
                    continue
            out.append({"id": "AC-28", "finding": "unexpected pytest plugin", "plugin": p.get("name"),
                        "file": f, "run": session["label"]})
        return out

    def tool_run(self, label, root, step, mode, extra_spec=None, profile="tool", audit=False, sites=()):
        wd = step["wd"]
        cwd = root / wd if wd else root
        script = str(cwd / step["script"])
        pythonpath = step["env"].get("PYTHONPATH")
        if mode == "VERBATIM":
            return self.runner.verbatim(label, cwd, [step["script"], *step.get("args", [])], pythonpath=pythonpath)
        sys_path = [os.path.dirname(script)]
        for entry in (pythonpath or "").split(":"):
            if entry:
                sys_path.append(str((cwd / entry).resolve()))
        spec = {"script": script, "args": step.get("args", [])}
        spec.update(extra_spec or {})
        return self.runner.hardened(label, root, cwd, profile, sys_path, spec, pythonpath=pythonpath,
                                    audit=audit, sites=sites)

    def evidence_of(self, stdout, prefix):
        lines = [l for l in stdout.split("\n") if l.startswith(prefix + "=")]
        if len(lines) != 1:
            return None, None
        return lines[0], json.loads(lines[0].split("=", 1)[1])

    def dynamic_phase(self):
        sb, R, T = self.sb, self.R, self.T
        K, BRANCH = self.K, self.BRANCH
        canon_ref = "refs/remotes/origin/" + BRANCH
        vs = [V for V in self.Vs if self.v_applies.get(V)]
        self.vs = vs
        tR = sb.tree(R)
        site_list = [(s["path"], s["kind"], s["name"]) for s in self.sites]
        tool_steps_R = [s for s in self.wf_R["steps"] if s["kind"] == "tool"]
        pytest_steps_R = [s for s in self.wf_R["steps"] if s["kind"] == "pytest" and
                          any(not a.startswith("-") for a in s["args"])]
        full_steps_R = [s for s in self.wf_R["steps"] if s["kind"] == "pytest" and
                        not any(not a.startswith("-") for a in s["args"])]
        # Π: T restricted to paths(R), parent T (AC-33)
        tT = sb.tree(T)
        pi_entries = {p: tT[p] for p in tR if p in tT}
        pi_tree = sb.make_tree(pi_entries)
        self.pi = sb.commit_tree(pi_tree, [T], "track-c-fpia projection")
        jobs = {}

        def lane_R():
            root, entries = self.materialise("R", R, {canon_ref: K})
            out = {"tools": [], "pytest": [], "site": None, "probe": None}
            for st in tool_steps_R:
                res = self.tool_run("R-hardened-" + st["script"], root, st, "HARDENED")
                out["tools"].append((st, res))
            out["tree_after_tools"] = fgit.verify_tree(root, entries, self.out_dirs(root))
            for i, st in enumerate(pytest_steps_R):
                files = self.expand(st, set(entries))
                out["pytest"].append((st, self.pytest_session("R", "R-step-%d" % i, root, entries, st["wd"], files,
                                                              track_c=True, audit=False)))
            out["site"] = self.site_eval("R-site", root)
            out["probe"] = self.registration_probe("R-probe", root, None)
            return out

        def lane_R_verbatim():
            root, entries = self.materialise("R-verbatim", R, {canon_ref: K})
            out = {"tools": [], "pytest": []}
            for st in tool_steps_R:
                out["tools"].append((st, self.tool_run("R-verbatim-" + st["script"], root, st, "VERBATIM")))
            for i, st in enumerate(pytest_steps_R):
                files = self.expand(st, set(entries))
                rootdir_rel, _ = self.determine_rootdir(root, st["wd"], files)
                junit = self.runner.work / "junit" / ("R-verbatim-%d.xml" % i)
                junit.parent.mkdir(parents=True, exist_ok=True)
                res = self.runner.verbatim("R-verbatim-step-%d" % i, root / st["wd"],
                                           ["-m", "pytest", *st["args"][:0], "-q", *files, "-p", "no:cacheprovider",
                                            "--junitxml", str(junit)], pythonpath=st["env"].get("PYTHONPATH"))
                out["pytest"].append((st, {"rc": res.rc, "junit": frun.junit_counts(junit),
                                           "cases": self.junit_cases(junit, rootdir_rel)}))
            return out

        def lane_E(E):
            steps = [s for s in self.workflow(E)["steps"] if s["kind"] == "tool"]
            tE = sb.tree(E)
            models = {}
            for st in steps:
                models[st["script_path"]] = fd.ToolModel(st["script_path"], sb.blob(tE[st["script_path"]].sha))
            c6e = [m for m in models.values() if m.kind == "C6"]
            if len(c6e) != 1:
                return {"error": "no unique C6 tool at evidence head"}
            ref = {"refs/remotes/origin/" + c6e[0].consts["BRANCH"]: c6e[0].consts["CANONICAL"]}
            root, entries = self.materialise("E-" + E[:12], E, ref)
            out = {"models": models, "tools": [], "canonical_ref_pinned_to": c6e[0].consts["CANONICAL"],
                   "site": None}
            for st in steps:
                out["tools"].append((st, self.tool_run("E-%s-%s" % (E[:12], st["script"]), root, st, "HARDENED")))
            out["tree_after"] = fgit.verify_tree(root, entries, self.out_dirs(root, models.values()))
            out["site"] = self.site_eval("E-site-" + E[:12], root, at=E)
            out["log_runtime"] = self.ci_log_runtime(E)
            return out

        def lane_pi():
            root, entries = self.materialise("PI", self.pi, {canon_ref: K})
            return {"tools": [(st, self.tool_run("PI-" + st["script"], root, st, "HARDENED")) for st in tool_steps_R]}

        def lane_V(V):
            root, entries = self.materialise("V-" + V[:12], V, {canon_ref: K})
            out = {"pytest": [], "v2": None, "replay": []}
            for i, st in enumerate(pytest_steps_R):
                files = self.expand(st, set(entries))
                out["pytest"].append((st, self.pytest_session("V", "V-step-%d" % i, root, entries, st["wd"], files,
                                                              audit=False)))
            v2files = self.v2_test_files(set(entries))
            if v2files:
                out["v2"] = self.pytest_session("V", "V-v2", root, entries, "implementation",
                                                [f[len("implementation/"):] for f in v2files], audit=True,
                                                sites=site_list)
            for cmd in self.replay_commands(V):
                out["replay"].append((cmd, self.script_run("V-replay-" + cmd["script"].rsplit("/", 1)[-1], root, cmd)))
            return out

        def lane_T():
            root, entries = self.materialise("T", T, {canon_ref: K})
            self.T_root = root
            out = {"pytest": [], "v2": None, "replay": [], "main_blocks": [], "site": None, "probe": None,
                   "ns_extra": None}
            for i, st in enumerate(pytest_steps_R):
                files = self.expand(st, set(entries))
                out["pytest"].append((st, self.pytest_session("T", "T-step-%d" % i, root, entries, st["wd"], files,
                                                              audit=True, sites=site_list)))
            extra = self.ns_uncovered_tests(set(entries), pytest_steps_R)
            if extra:
                out["ns_extra"] = self.pytest_session("T", "T-ns-extra", root, entries, "implementation",
                                                      [f[len("implementation/"):] for f in extra], audit=True,
                                                      sites=site_list)
            v2files = self.v2_test_files(set(entries))
            if v2files and vs:
                out["v2"] = self.pytest_session("T", "T-v2", root, entries, "implementation",
                                                [f[len("implementation/"):] for f in v2files], audit=True,
                                                sites=site_list)
            for V in vs:
                for cmd in self.replay_commands(V):
                    out["replay"].append((cmd, self.script_run("T-replay-" + cmd["script"].rsplit("/", 1)[-1], root, cmd,
                                                               audit=True, sites=site_list)))
            out["site"] = self.site_eval("T-site", root)
            out["entries"] = entries
            out["root"] = root
            return out

        def lane_T_full():
            root, entries = self.materialise("T-full", T, {canon_ref: K})
            st = full_steps_R[0] if full_steps_R else {"wd": "implementation", "args": ["-q"], "env": {"PYTHONPATH": "src"}}
            extra = ["--continue-on-collection-errors"]
            dsel = self.network_deselect()
            if dsel["valid"]:
                extra += ["--deselect", NETWORK_NODE]
            sess = self.pytest_session("T-full", "T-full", root, entries, st["wd"], [], extra=extra,
                                       track_c=False, audit=False)
            sess["deselect"] = dsel
            sess["tree_after"] = fgit.verify_tree(root, entries, ())
            return sess

        def lane_T_frozen():
            repo_canon = self.repo_canonical()
            refs = {canon_ref: repo_canon} if repo_canon else {}
            root, entries = self.materialise("T-frozen", T, refs)
            out = {"canonical_ref": {"name": canon_ref, "value": repo_canon}, "steps": []}
            if self.wf_T is None:
                out["error"] = "Track C workflow absent at T"
                return out
            dsel = self.network_deselect()
            for i, st in enumerate(self.wf_T["steps"]):
                if st["kind"] in ("git", "pip"):
                    out["steps"].append({"step": st["name"], "kind": st["kind"], "executed": False,
                                         "deviation": "network/setup step not executed; FPIA sets the canonical ref "
                                                      "from --repo and verifies pins (AC-36)"})
                    continue
                if st["kind"] == "pytest":
                    files = self.expand(st, set(entries))
                    is_full = not any(not a.startswith("-") for a in st["args"])
                    args = ["-m", "pytest", *[a for a in st["args"] if a.startswith("-")], *files]
                    dev = None
                    if is_full and dsel["valid"]:
                        args += ["--deselect", NETWORK_NODE]
                        dev = "single live-network node deselected (PIW ruling; disclosed)"
                    res = self.runner.verbatim("T-frozen-step-%d" % i, root / st["wd"], args,
                                               pythonpath=st["env"].get("PYTHONPATH"))
                    tail = res.stdout.strip().split("\n")[-1] if res.stdout.strip() else ""
                    out["steps"].append({"step": st["name"], "kind": "pytest", "rc": res.rc, "deviation": dev,
                                         "summary": re.sub(r" in [0-9.]+s( \([0-9:]+\))?", "", tail)})
                elif st["kind"] == "tool":
                    res = self.tool_run("T-frozen-" + st["script"], root, st, "VERBATIM")
                    line = [l for l in res.stdout.split("\n") if "_EVIDENCE=" in l]
                    err = [l for l in res.stderr.strip().split("\n") if l][-1:] if res.stderr.strip() else []
                    model = self.tools.get(st["script_path"]) or (fd.ToolModel(st["script_path"], sb.read(T, st["script_path"]))
                                                                 if sb.read(T, st["script_path"]) else None)
                    matched = None
                    if err and model:
                        for msg in model.raise_messages():
                            if msg and msg in err[0]:
                                matched = msg
                                break
                    out["steps"].append({"step": st["name"], "kind": "tool", "tool": st["script_path"],
                                         "blob": sb.tree(T).get(st["script_path"]).sha if sb.tree(T).get(st["script_path"]) else None,
                                         "rc": res.rc, "evidence_line_sha256": sha256(line[0].encode()) if line else None,
                                         "first_error": err[0][:400] if err else None, "matched_tool_message": matched})
                else:
                    out["steps"].append({"step": st["name"], "kind": st["kind"], "executed": False,
                                         "deviation": "unrecognised step; NOT_RUN"})
            return out

        jobs["R"] = lane_R
        jobs["R-verbatim"] = lane_R_verbatim
        for E in self.frozen["heads"]:
            jobs["E:" + E] = (lambda E=E: lane_E(E))
        jobs["PI"] = lane_pi
        for V in vs:
            jobs["V:" + V] = (lambda V=V: lane_V(V))
        jobs["T"] = lane_T
        jobs["T-full"] = lane_T_full
        jobs["T-frozen"] = lane_T_frozen
        if self.opts["lanes"] is not None:
            wanted = set(self.opts["lanes"])
            jobs = {k: v for k, v in jobs.items() if k.split(":")[0] in wanted}
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.opts["max_workers"]) as ex:
            futs = {ex.submit(fn): name for name, fn in jobs.items()}
            for fut in concurrent.futures.as_completed(futs):
                name = futs[fut]
                try:
                    results[name] = fut.result()
                except Exception as exc:  # recorded; components become NOT_RUN
                    import traceback
                    results[name] = {"error": "%s: %s" % (type(exc).__name__, exc),
                                     "traceback": traceback.format_exc()[-2000:]}
        self.lanes = results
        # dynamic A_V closure from v2 reads at V (review MEDIUM)
        for V in vs:
            v2 = (results.get("V:" + V) or {}).get("v2")
            reads = set()
            if v2 and v2["result"].trace:
                for ev in v2["result"].trace.get("events", []):
                    if ev.get("event") == "read":
                        reads.add(ev["path"])
            av_dyn, reasons = fchk.derive_av(sb, R, V, self.proj, self.tcm_R, dynamic=reads)
            new = av_dyn - self.av
            if new:
                self.av |= new
                self.av_reasons.update({p: reasons[p] for p in new})
                self.result["derivation"]["projection"]["A_V_dynamic_additions"] = sorted(new)
                _, v2checks, _ = fchk.projection_identity(sb, R, self.Vs, T, self.proj, self.av, self.v_applies)
                self.v2_checks = v2checks
        # T lane: main blocks, counterfactual and probe need the code identity values first
        tl = results.get("T") or {}
        if "error" not in tl and tl:
            self.post_T_runs(tl)

    # helpers for the dynamic phase ------------------------------------------------------------------
    def out_dirs(self, root, models=None):
        dirs = set()
        for m in (models or self.tools.values()):
            for d in m.out_dirs:
                dirs.add("implementation/" + d)
        return sorted(dirs)

    def expand(self, step, files):
        out = []
        for a in step["args"]:
            if a.startswith("-"):
                continue
            out.extend(fd.expand_glob(a, files, step["wd"]))
        return out

    def v2_test_files(self, files):
        return sorted(p for p in self.av if p in files and p.rsplit("/", 1)[-1].startswith("test_")
                      and p.endswith(".py") and p.startswith("implementation/"))

    def ns_uncovered_tests(self, files, steps):
        covered = set()
        for st in steps:
            for f in self.expand(st, files):
                covered.add((st["wd"].rstrip("/") + "/" + f) if st["wd"] else f)
        tR = self.sb.tree(self.R)
        return sorted(p for p in tR if self.proj.ns(p) and p.rsplit("/", 1)[-1].startswith("test_")
                      and p.endswith(".py") and p not in covered and p.startswith("implementation/"))

    def replay_commands(self, V):
        out = []
        tV = self.sb.tree(V)
        for p in sorted(tV):
            if not (p.startswith(fd.WORKFLOW_DIR) and p.endswith((".yml", ".yaml"))):
                continue
            wf = fd.parse_workflow(self.sb.blob(tV[p].sha).decode("utf-8", "replace"))
            for st in wf["steps"]:
                kind, env, rest = fd.classify_step(st["run"].split(">")[0].strip())
                if kind != "tool" or env:
                    continue
                wd = st["wd"] or wf["defaults_wd"] or ""
                script = (wd.rstrip("/") + "/" + rest[0]) if wd else rest[0]
                if script in self.av and script.endswith(".py"):
                    out.append({"workflow": p, "script": script, "wd": wd, "args": rest[1:]})
        uniq = {}
        for c in out:
            uniq.setdefault((c["script"], tuple(c["args"]), c["wd"]), c)
        return list(uniq.values())

    def script_run(self, label, root, cmd, audit=False, sites=()):
        cwd = root / cmd["wd"] if cmd["wd"] else root
        script = str((cwd / cmd["script"].split("/", cmd["wd"].count("/") + 1)[-1]) if cmd["wd"] else root / cmd["script"])
        return self.runner.hardened(label, root, cwd, "script", [os.path.dirname(script)],
                                    {"script": script, "args": cmd["args"]}, audit=audit, sites=sites)

    def site_eval(self, label, root, at=None):
        specs = []
        tree = self.sb.tree(at) if at else None
        for s in self.sites:
            if tree is not None and s["path"] not in tree:
                continue
            specs.append([s["module"], s["kind"], s["name"]])
        if not specs:
            return {"values": {}, "rc": 0}
        sys_path = [str(root / "implementation"), str(root / "implementation" / "src")]
        res = self.runner.hardened(label, root, root / "implementation", "site_eval", sys_path,
                                   {"site_specs": specs}, pythonpath="src")
        return {"values": (res.trace or {}).get("site_values"), "rc": res.rc, "result": res}

    def registration_probe(self, label, root, bound_value):
        call_sites = [s for s in self.sites if s["kind"] == "call"]
        if not call_sites:
            return {"status": "NOT_RUN", "detail": "no function-kind code identity site"}
        s = call_sites[0]
        validator = fd.binding_validator(self.sb.read(self.R, s["path"]), s["path"], s["name"])
        if validator is None:
            return {"status": "NOT_RUN", "detail": "binding validator not found"}
        fixture = None
        for kind in ("C8_PARTIAL", "C7", "C6"):
            t = self.by_kind.get(kind)
            if t is None:
                continue
            mod = t.fixture["module"]
            path = "implementation/" + mod.replace(".", "/") + ".py"
            data = self.sb.read(self.R, path)
            if data is None:
                continue
            names = {n.name for n in fd.parse_py(data, path).body if hasattr(n, "name")}
            if {"prepare_source", "setup", "register"} <= names:
                fixture = mod
                break
        if fixture is None:
            return {"status": "NOT_RUN", "detail": "fixture API absent"}
        return {"validator": validator, "fixture_module": fixture, "site": s, "root": root}

    def run_probe(self, label, info, root, bound_value):
        sys_path = [str(root / "implementation"), str(root / "implementation" / "src")]
        res = self.runner.hardened(label, root, root / "implementation", "registration_probe", sys_path,
                                   {"probe": {"fixture_module": info["fixture_module"], "key": info["validator"]["key"],
                                              "bound_value": bound_value}}, pythonpath="src")
        return dict((res.trace or {}).get("probe") or {"status": "NOT_RUN", "rc": res.rc,
                                                       "stderr": res.stderr[-500:]}, rc=res.rc)

    def network_deselect(self):
        file_part = "implementation/" + NETWORK_NODE.split("::", 1)[0]
        r, t = self.sb.tree(self.R).get(file_part), self.sb.tree(self.T).get(file_part)
        valid = r is not None and t is not None and r == t
        return {"node": NETWORK_NODE, "file": file_part, "valid": valid, "present_at_T": t is not None,
                "rule": "honoured only while its file is byte-identical to R's (PIW ruling); disclosed deviation"}

    def repo_canonical(self):
        ref = "refs/fpia/src/remotes/origin/" + self.BRANCH
        out = self.sb.run(["rev-parse", "--verify", "--quiet", ref], check=False).stdout.decode().strip()
        return out or None

    def ci_log_runtime(self, E):
        logs = [x for x in self.frozen["logs"] if x["head"] == E]
        dists = None
        for p in sorted({x["path"] for x in logs}):
            text = self.sb.read(self.R, p).decode("utf-8", "replace")
            for line in text.split("\n"):
                if "Successfully installed " in line:
                    names = line.split("Successfully installed ", 1)[1].split()
                    dists = sorted(names)
        return dists

    def junit_cases(self, junit, rootdir_rel):
        import xml.etree.ElementTree as ET
        try:
            root = ET.parse(junit).getroot()
        except (ET.ParseError, OSError):
            return None
        out = {}
        for case in root.iter("testcase"):
            name = "%s::%s" % (case.get("classname"), case.get("name"))
            outcome = "passed"
            for child in case:
                if child.tag in ("failure", "error", "skipped"):
                    outcome = child.tag
            out[name] = outcome
        return out

    # -- post-processing of T runs that need site values -------------------------------------------------
    def post_T_runs(self, tl):
        root = tl["root"]
        site_list = [(s["path"], s["kind"], s["name"]) for s in self.sites]
        r_site = (self.lanes.get("R") or {}).get("site") or {}
        t_site = tl.get("site") or {}
        self.site_R = r_site.get("values")
        self.site_T = t_site.get("values")
        tool_steps = [s for s in self.wf_R["steps"] if s["kind"] == "tool"]
        mains = []

        def pins_for(values):
            pins = []
            for s in self.sites:
                key = s["module"] + ":" + s["name"]
                if values is None or key not in values:
                    continue
                pins.append({"module": s["module"], "kind": s["kind"], "name": s["name"], "value": values[key],
                             "importers": s["importers"]})
            return pins

        def run_main(label, st, pins):
            model = self.tools[st["script_path"]]
            res = self.tool_run(label, root, st, "HARDENED", profile="main_block",
                                extra_spec={"audit_line": model.audit_call["lineno"], "pins": pins},
                                audit=True, sites=site_list)
            line, ev = self.evidence_of(res.stdout, model.prefix)
            for d in self.out_dirs(root, [model]):
                shutil.rmtree(root / d, ignore_errors=True)
            return {"label": label, "tool": st["script_path"], "rc": res.rc, "evidence": ev,
                    "stderr_tail": res.stderr.strip().split("\n")[-1:] if res.stderr.strip() else [],
                    "result": res, "pins": [p["module"] + ":" + p["name"] for p in pins]}

        for st in tool_steps:
            mains.append(run_main("T-main-" + st["script"], st, []))
        cf = []
        if self.site_R is not None:
            for st in tool_steps:
                cf.append({"reference": "R", **run_main("T-cf-R-" + st["script"], st, pins_for(self.site_R))})
        for E in self.frozen["heads"]:
            le = self.lanes.get("E:" + E) or {}
            if "error" in le or not le:
                continue
            values = (le.get("site") or {}).get("values")
            if not values:
                continue
            applicable, diff = self.cf_applicable(E)
            for st_e, res_e in le["tools"]:
                kind = le["models"][st_e["script_path"]].kind
                st_t = [s for s in tool_steps if self.tools[s["script_path"]].kind == kind]
                if not st_t:
                    continue
                if not applicable:
                    cf.append({"reference": E, "tool": st_t[0]["script_path"], "status": "NOT_APPLICABLE",
                               "detail": "Track C sources differ between E and T", "differing": diff[:10]})
                    continue
                cf.append({"reference": E, **run_main("T-cf-%s-%s" % (E[:12], st_t[0]["script"]), st_t[0],
                                                      pins_for(values))})
        tl["main_blocks"] = mains
        tl["counterfactual"] = cf
        info = self.registration_probe("probe", root, None)
        if "validator" in info and self.site_R and self.site_T:
            s = info["site"]
            key = s["module"] + ":" + s["name"]
            tl["probe"] = {"info": {k: v for k, v in info.items() if k not in ("root", "site")},
                           "T": self.run_probe("T-probe", info, root, self.site_R.get(key))}
            r_root = self.lane_dir("R")
            tl["probe"]["R_control"] = self.run_probe("R-probe-control", info, r_root, self.site_R.get(key))
        else:
            tl["probe"] = {"status": "NOT_RUN", "detail": info.get("detail", "site values unavailable")}

    def cf_applicable(self, E):
        tE, tT = self.sb.tree(E), self.sb.tree(self.T)
        diff = sorted(p for p in tE if p.endswith(".py") and self.proj.ns(p) and p not in self.tools
                      and tE[p] != tT.get(p))
        return (not diff), diff

    # -- composition of components ---------------------------------------------------------------------
    def compose_components(self):
        r, sb, R, T = self.result, self.sb, self.R, self.T
        lanes = self.lanes
        tR, tT = sb.tree(R), sb.tree(T)
        allowed = set(tR) | (self.av if getattr(self, "vs", None) else set())
        complement = set(tT) - allowed
        site_list = [(s["path"], s["kind"], s["name"]) for s in self.sites]
        lane_errors = {k: v["error"] for k, v in lanes.items() if isinstance(v, dict) and "error" in v}
        r["lane_errors"] = lane_errors
        # ---------------- historical (AC-11, AC-12, review HIGH #1) ----------------
        hist_checks = []
        hist = "PRESERVED"
        if self.frozen["unbound"]:
            hist = "NOT_RUN"
        replays = {}
        for E in self.frozen["heads"]:
            le = lanes.get("E:" + E)
            if not le or "error" in le:
                hist_checks.append({"id": "AC-12", "status": "NOT_RUN", "head": E, "detail": (le or {}).get("error")})
                hist = "NOT_RUN" if hist == "PRESERVED" else hist
                continue
            tools = []
            for st, res in le["tools"]:
                model = le["models"][st["script_path"]]
                line, ev = self.evidence_of(res.stdout, model.prefix)
                tools.append({"path": st["script_path"], "blob": sb.tree(E)[st["script_path"]].sha, "rc": res.rc,
                              "kind": model.kind, "evidence_sha256": sha256(line.encode()) if line else None,
                              "line": line, "evidence": ev, "model": model})
                if res.rc != 0 or line is None:
                    hist_checks.append({"id": "AC-12", "status": "NOT_PRESERVED", "head": E, "tool": st["script_path"],
                                        "detail": "replay rc %d or no evidence line" % res.rc,
                                        "stderr_tail": res.stderr.strip().split("\n")[-1:]})
                    hist = "NOT_PRESERVED"
                for f in frun.check_trace(res, self.lane_dir("E-" + E[:12]), sb.tree(E), set(sb.tree(E)),
                                          self.baseline_meta, track_c=False, launcher_dir=self.runner.launch_dir):
                    hist_checks.append(dict(f, status="NOT_RUN", head=E))
                    hist = "NOT_RUN" if hist == "PRESERVED" else hist
            # runtime of the Frozen CI run vs the replay (review LOW)
            logged = le.get("log_runtime")
            used = self.payload_distributions(le["tools"])
            if logged is not None:
                logged_names = {x.rsplit("-", 1)[0].lower(): x.rsplit("-", 1)[1] for x in logged}
                inst = frun.distributions()
                bad = sorted(d for d in used if d not in logged_names or logged_names[d] != inst.get(d))
                if bad:
                    hist_checks.append({"id": "AC-12.runtime", "status": "NOT_RUN", "head": E,
                                        "detail": "replay imported distributions outside the Frozen CI runtime", "dists": bad})
                    hist = "NOT_RUN" if hist == "PRESERVED" else hist
            if le.get("tree_after"):
                hist_checks.append({"id": "AC-31", "status": "NOT_RUN", "head": E, "detail": "tree changed during replay",
                                    "problems": [list(p) for p in le["tree_after"][:5]]})
                hist = "NOT_RUN" if hist == "PRESERVED" else hist
            replays[E] = {"tools": tools, "canonical_ref_pinned_to": le["canonical_ref_pinned_to"],
                          "logged_runtime": logged, "payload_distributions": sorted(used)}
        # logged lines byte for byte
        for x in self.frozen["logs"]:
            rp = replays.get(x["head"])
            if rp is None:
                continue
            got = [t for t in rp["tools"] if t["line"] and t["line"].split("=", 1)[0] == x["prefix"]]
            if not got:
                hist_checks.append({"id": "AC-12", "status": "NOT_RUN", "detail": "no replayed tool emits this prefix",
                                    "path": x["path"], "line": x["line"]})
                hist = "NOT_RUN" if hist == "PRESERVED" else hist
            elif got[0]["line"] != x["body"]:
                hist_checks.append({"id": "AC-12", "status": "NOT_PRESERVED", "detail": "logged evidence line not "
                                    "reproduced byte for byte", "path": x["path"], "line": x["line"]})
                hist = "NOT_PRESERVED"
            else:
                r["equality_claims"].append({"claim": "logged evidence line %s:%d reproduced" % (x["path"], x["line"]),
                                             "source": "EXACT_CONDITION_REPLAY_UNMODIFIED_TOOL", "head": x["head"]})
        # records
        for rec in self.frozen["records"]:
            data = json.loads(sb.blob(rec["blob"]))
            for emb in rec["embedded"]:
                rp = replays.get(emb["head"])
                if rp is None:
                    continue
                obj = data
                for part in emb["at"]:
                    obj = obj[part]
                match = [t for t in rp["tools"] if t["evidence"] is not None and set(t["evidence"]) == set(obj)
                         and set(obj) == set(t["model"].evidence_keys)]
                if not match:
                    hist_checks.append({"id": "AC-11", "status": "NOT_RUN", "detail": "embedded evidence has no bound "
                                        "tool at its head", "path": rec["path"], "at": emb["at"]})
                    hist = "NOT_RUN" if hist == "PRESERVED" else hist
                    continue
                ev = match[0]["evidence"]
                if ev != obj:
                    hist_checks.append({"id": "AC-12", "status": "NOT_PRESERVED", "detail": "embedded evidence differs "
                                        "from the exact-head replay", "path": rec["path"], "at": emb["at"]})
                    hist = "NOT_PRESERVED"
                    continue
                problems = self.record_claims(data, ev, emb["head"])
                if problems:
                    hist_checks.append({"id": "AC-12", "status": "NOT_PRESERVED", "detail": "record claims differ from "
                                        "the replay", "path": rec["path"], "problems": problems})
                    hist = "NOT_PRESERVED"
                else:
                    r["equality_claims"].append({"claim": "record %s %s deep-equals replay" % (rec["path"], "/".join(map(str, emb["at"]))),
                                                 "source": "EXACT_CONDITION_REPLAY_UNMODIFIED_TOOL", "head": emb["head"]})
            if not rec["embedded"] and "head" in rec:
                rp = replays.get(rec["head"])
                if rp is None:
                    continue
                problems = self.log_record_claims(rec, data, rp)
                if problems:
                    hist_checks.append({"id": "AC-12", "status": problems[0].get("status", "NOT_PRESERVED"),
                                        "detail": "verification record differs from the replay", "path": rec["path"],
                                        "problems": problems})
                    hist = "NOT_PRESERVED" if any(p.get("status", "NOT_PRESERVED") == "NOT_PRESERVED" for p in problems) else (
                        "NOT_RUN" if hist == "PRESERVED" else hist)
                else:
                    r["equality_claims"].append({"claim": "verification record %s consistent with replay" % rec["path"],
                                                 "source": "EXACT_CONDITION_REPLAY_UNMODIFIED_TOOL", "head": rec["head"]})
        # Frozen evidence byte identity in T (CDR-014 §3)
        for path in sorted({x["path"] for x in self.frozen["logs"]} | {x["path"] for x in self.frozen["records"]}):
            if path in tR and tT.get(path) != tR[path]:
                hist_checks.append({"id": "AC-16", "status": "NOT_PRESERVED", "detail": "Frozen evidence bytes changed in T",
                                    "path": path})
                hist = "NOT_PRESERVED"
        # R replay under its own conditions (no Actions equality claim)
        lr = lanes.get("R") or {}
        r_tools = []
        if "error" in lr or not lr:
            hist_checks.append({"id": "AC-12", "status": "NOT_RUN", "detail": "R replay lane unavailable",
                                "error": lr.get("error")})
            hist = "NOT_RUN" if hist == "PRESERVED" else hist
        else:
            for st, res in lr["tools"]:
                model = self.tools[st["script_path"]]
                line, ev = self.evidence_of(res.stdout, model.prefix)
                r_tools.append({"path": st["script_path"], "rc": res.rc, "evidence_sha256": sha256(line.encode()) if line else None})
                if res.rc != 0:
                    hist_checks.append({"id": "AC-12", "status": "NOT_PRESERVED", "detail": "R replay rc != 0",
                                        "tool": st["script_path"]})
                    hist = "NOT_PRESERVED"
        self.st["historical_frozen_identity"] = {"PRESERVED": "HISTORICAL_FROZEN_IDENTITY_PRESERVED",
                                                 "NOT_PRESERVED": "HISTORICAL_FROZEN_IDENTITY_NOT_PRESERVED",
                                                 "NOT_RUN": "NOT_RUN"}[hist]
        r["historical_frozen_identity"] = {"status": self.st["historical_frozen_identity"], "checks": hist_checks,
                                           "r_replay": {"canonical_ref_pinned_to": self.K, "tools": r_tools,
                                                        "note": "no Actions-equality claim for R"},
                                           "replays": {E: {"canonical_ref_pinned_to": v["canonical_ref_pinned_to"],
                                                           "logged_runtime": v["logged_runtime"],
                                                           "payload_distributions": v["payload_distributions"],
                                                           "tools": [{k: t[k] for k in ("path", "blob", "rc", "kind", "evidence_sha256")}
                                                                     for t in v["tools"]]}
                                                       for E, v in sorted(replays.items())}}
        # ---------------- code identity (AC-08, AC-09) ----------------
        ci = "NOT_RUN"
        vals = {}
        site_R = (lr.get("site") or {}).get("values") if lr and "error" not in lr else None
        lt = lanes.get("T") or {}
        site_T = (lt.get("site") or {}).get("values") if lt and "error" not in lt else None
        if site_R and site_T and set(site_R) == set(site_T) and len(site_R) == len(self.sites):
            same = all(site_R[k] == site_T[k] for k in site_R)
            ci = "CODE_IDENTITY_SAME" if same else "CODE_IDENTITY_DIVERGED"
            vals = {k: {"R": site_R[k], "T": site_T[k]} for k in sorted(site_R)}
        vs_heads = {}
        for E in self.frozen["heads"]:
            le = lanes.get("E:" + E) or {}
            if le and "error" not in le:
                vs_heads[E] = (le.get("site") or {}).get("values")
        self.st["code_identity"] = ci
        r["code_identity"] = {"status": ci, "site_values": vals, "vs_frozen_evidence_heads": vs_heads,
                              "evaluation": "UNMODIFIED sites evaluated in the hardened child on raw-blob trees; never pinned"}
        if ci == "CODE_IDENTITY_DIVERGED":
            r["code_identity"]["registration_binding"] = (
                "PRIOR_TRACK_C_REGISTRATIONS_FAIL_CLOSED_ON_T (CDR-014 §11); new registrations only on the final "
                "canonical candidate")
        # ---------------- projection (AC-14..20, AC-33) ----------------
        proj = "PRESERVED"
        pchecks = list(self.projection_checks)
        if any(c["status"] == "NOT_PRESERVED" for c in pchecks):
            proj = "NOT_PRESERVED"
        for c in self.provenance_checks:
            if c["status"] == "FAIL":
                proj = "NOT_PRESERVED"
            elif c["status"] == "NOT_RUN" and proj == "PRESERVED":
                proj = "NOT_RUN"
        for l in self.dr_linkage:
            if l["status"] != "PASS" and proj == "PRESERVED":
                proj = "NOT_RUN"
                pchecks.append({"id": "AC-17", "status": "NOT_RUN", "detail": "register linkage evidence not located",
                                "path": l["path"]})
        lp = lanes.get("PI") or {}
        pi_info = {"pi_commit": self.pi, "pi_tree": sb.tree_id(self.pi) if self.pi else None, "tools": []}
        if not lp or "error" in lp or not lr or "error" in lr:
            proj = "NOT_RUN" if proj == "PRESERVED" else proj
        else:
            bpaths = fd.boundary_paths(self.by_kind)
            r_ev = {}
            for st, res in lr["tools"]:
                model = self.tools[st["script_path"]]
                r_ev[st["script_path"]] = self.evidence_of(res.stdout, model.prefix)[1]
            for st, res in lp["tools"]:
                model = self.tools[st["script_path"]]
                line, ev = self.evidence_of(res.stdout, model.prefix)
                entry = {"tool": st["script_path"], "rc": res.rc}
                if res.rc != 0 or ev is None or r_ev.get(st["script_path"]) is None:
                    entry["status"] = "NOT_PRESERVED"
                    entry["stderr_tail"] = res.stderr.strip().split("\n")[-1:]
                    proj = "NOT_PRESERVED"
                else:
                    a, removed = fd.strip_evidence(ev, bpaths.get(model.kind, []))
                    b, _ = fd.strip_evidence(r_ev[st["script_path"]], bpaths.get(model.kind, []))
                    entry["stripped_paths"] = removed
                    if a != b:
                        entry["status"] = "NOT_PRESERVED"
                        proj = "NOT_PRESERVED"
                    else:
                        entry["status"] = "PRESERVED"
                        r["equality_claims"].append({"claim": "projection replay strip-equals R for %s" % st["script_path"],
                                                     "source": "PROJECTION_REPLAY_UNMODIFIED_TOOL"})
                pi_info["tools"].append(entry)
        self.st["track_c_projection"] = {"PRESERVED": "TRACK_C_PROJECTION_PRESERVED",
                                         "NOT_PRESERVED": "TRACK_C_PROJECTION_NOT_PRESERVED", "NOT_RUN": "NOT_RUN"}[proj]
        r["track_c_projection"].update({"status": self.st["track_c_projection"], "checks": pchecks,
                                        "projection_replay": pi_info})
        if proj == "PRESERVED":
            r["equality_claims"].append({"claim": "every projection path of R has identical git object identity in T "
                                                  "(or is an authenticated V version / append)", "source": "GIT_OBJECT_IDENTITY"})
        # ---------------- interference (AC-22..35) ----------------
        inter_findings = list(self.static_findings)
        inter_nr = []
        vs = getattr(self, "vs", [])
        ref_lane = lanes.get("V:" + vs[0]) if vs else lr
        ref_name = ("V:" + vs[0]) if vs else "R"
        targeted = []
        t_ok = bool(lt) and "error" not in lt
        ref_ok = bool(ref_lane) and "error" not in ref_lane
        if not t_ok:
            inter_nr.append("T lane unavailable")
        else:
            if ref_ok:
                for (st, sT), (st2, sRef) in zip(lt["pytest"], ref_lane["pytest"]):
                    cmp = self.compare_sessions(sT, sRef, complement, allowed, site_list, lt["root"], lt["entries"])
                    targeted.append(cmp["record"])
                    inter_findings += cmp["findings"]
                    inter_nr += cmp["not_run"]
            else:
                inter_nr.append("reference lane unavailable")
                for st, sT in lt["pytest"]:
                    cmp = self.compare_sessions(sT, None, complement, allowed, site_list, lt["root"], lt["entries"])
                    targeted.append(cmp["record"])
                    inter_findings += cmp["findings"]
            if lt.get("ns_extra"):
                s = lt["ns_extra"]
                cmp = self.compare_sessions(s, None, complement, allowed, site_list, lt["root"], lt["entries"])
                targeted.append(cmp["record"])
                inter_findings += cmp["findings"]
                inter_nr += cmp["not_run"]
            # R lane steps also validate expansions R ⊆ reference
            if vs and lr and "error" not in lr and ref_ok:
                for (st, sR), (st2, sV) in zip(lr["pytest"], ref_lane["pytest"]):
                    if not set(sR["files"]) <= set(sV["files"]):
                        inter_findings.append({"id": "AC-30", "finding": "reference V drops R test files",
                                               "step": st["name"]})
            # main blocks (AC-34) and counterfactual (review HIGH, PIW D3-B)
            for m in lt.get("main_blocks", []):
                if m["rc"] != 0 or m["evidence"] is None:
                    inter_findings.append({"id": "AC-34", "finding": "Track C computation status failure on T",
                                           "tool": m["tool"], "rc": m["rc"], "stderr_tail": m["stderr_tail"]})
                inter_findings += frun.check_trace(m["result"], lt["root"], lt["entries"], allowed, self.baseline_meta,
                                                   track_c=True, complement=complement, sites=site_list, site_roots=self.site_roots(),
                                                   launcher_dir=self.runner.launch_dir)
            cf_records = []
            for c in lt.get("counterfactual", []):
                if c.get("status") == "NOT_APPLICABLE":
                    cf_records.append({k: c[k] for k in ("reference", "tool", "status", "detail")})
                    continue
                model = self.tools[c["tool"]]
                ref_ev = None
                if c["reference"] == "R":
                    for st, res in lr.get("tools", []):
                        if st["script_path"] == c["tool"]:
                            ref_ev = self.evidence_of(res.stdout, model.prefix)[1]
                else:
                    le = lanes.get("E:" + c["reference"]) or {}
                    for st, res in le.get("tools", []):
                        mm = le["models"][st["script_path"]]
                        if mm.kind == model.kind:
                            ref_ev = self.evidence_of(res.stdout, mm.prefix)[1]
                            ref_key = mm.result_key
                    if c["reference"] != "R" and ref_ev is not None:
                        ref_ev = {model.result_key: ref_ev.get(ref_key)}
                got = c["evidence"]
                ok = (c["rc"] == 0 and got is not None and ref_ev is not None
                      and got.get(model.result_key) == ref_ev.get(model.result_key))
                rec = {"reference": c["reference"], "tool": c["tool"], "rc": c["rc"], "pins": c["pins"],
                       "reproduced": ok, "evidence_class": "COUNTERFACTUAL_CODE_IDENTITY_NORMALISED"}
                cf_records.append(rec)
                if not ok:
                    inter_findings.append({"id": "COUNTERFACTUAL", "finding": "normalised code identity does not "
                                           "reproduce the reference computation (fail-only)", "reference": c["reference"],
                                           "tool": c["tool"], "rc": c["rc"]})
            # registration probe (AC-09)
            probe = lt.get("probe") or {}
            probe_rec = {"status": "NOT_RUN"}
            if "T" in probe:
                v = probe["info"]["validator"]
                tres, rres = probe["T"], probe["R_control"]
                expect_raise = ci == "CODE_IDENTITY_DIVERGED"
                if rres.get("status") != "REGISTERED":
                    probe_rec = {"status": "NOT_RUN", "detail": "R control did not register", "R_control": rres}
                elif tres.get("status") == "API_ABSENT":
                    probe_rec = {"status": "NOT_RUN", "detail": "fixture API absent"}
                elif ci not in ("CODE_IDENTITY_SAME", "CODE_IDENTITY_DIVERGED"):
                    probe_rec = {"status": "NOT_RUN", "detail": "code identity undetermined"}
                else:
                    raised_ok = (tres.get("status") == "RAISED" and tres.get("exception") == v["exception"]
                                 and tres.get("message") == v["message"])
                    agree = raised_ok if expect_raise else tres.get("status") == "REGISTERED"
                    probe_rec = {"status": "AGREES" if agree else "DISAGREES", "expected_raise": expect_raise,
                                 "T": tres, "validator": v}
                    if not agree:
                        inter_findings.append({"id": "AC-09", "finding": "registration binding probe disagrees with "
                                               "code identity", "probe": tres})
            else:
                probe_rec = {"status": "NOT_RUN", "detail": probe.get("detail")}
            r["integration_interference"]["registration_probe"] = probe_rec
            r["integration_interference"]["counterfactual"] = cf_records
            r["integration_interference"]["computations_on_T"] = [
                {"tool": m["tool"], "rc": m["rc"], "class": "INSTRUMENTED_MAIN_BLOCK / INTEGRATED_TREE_RAW",
                 "evidence_sha256": sha256(canonical_bytes(m["evidence"])) if m["evidence"] else None}
                for m in lt.get("main_blocks", [])]
            # v2 rerun (AC-22)
        v2 = "NOT_APPLICABLE"
        v2_detail = {"checks": list(self.v2_checks)}
        if vs:
            v2 = "PASS"
            if any(c["status"] == "FAIL" for c in self.v2_checks):
                v2 = "FAIL"
            lV = lanes.get("V:" + vs[0]) or {}
            if not lt or "error" in lt or not lV or "error" in lV:
                v2 = "NOT_RUN" if v2 == "PASS" else v2
            else:
                sT, sV = lt.get("v2"), lV.get("v2")
                if sT is None or sV is None:
                    if self.v2_test_files(set(tT)):
                        v2 = "NOT_RUN" if v2 == "PASS" else v2
                else:
                    cmp = self.compare_sessions(sT, sV, complement, allowed, site_list, lt["root"], lt["entries"])
                    v2_detail["tests"] = cmp["record"]
                    if cmp["findings"]:
                        v2 = "FAIL"
                        inter_findings += cmp["findings"]
                    if cmp["not_run"] and v2 == "PASS":
                        v2 = "NOT_RUN"
                rep = []
                for (cmd, resV), (cmd2, resT) in zip(lV.get("replay", []), lt.get("replay", [])):
                    same = resV.rc == 0 and resT.rc == 0 and resV.stdout == resT.stdout
                    rep.append({"script": cmd["script"], "workflow": cmd["workflow"], "rc_V": resV.rc, "rc_T": resT.rc,
                                "stdout_sha256_V": sha256(resV.stdout.encode()), "stdout_sha256_T": sha256(resT.stdout.encode()),
                                "byte_identical": same})
                    if not same:
                        v2 = "FAIL"
                    inter_findings += frun.check_trace(resT, lt["root"], lt["entries"], allowed, self.baseline_meta,
                                                       reference_sys_path=frun.tree_sys_path(resV, self.lane_dir("V-" + vs[0][:12])),
                                                       track_c=True, complement=complement, sites=site_list, site_roots=self.site_roots(),
                                                       launcher_dir=self.runner.launch_dir)
                if len(lV.get("replay", [])) != len(lt.get("replay", [])):
                    v2 = "NOT_RUN" if v2 == "PASS" else v2
                v2_detail["codex_replay"] = rep
            v2_detail["V"] = vs
            v2_detail["A_V_count"] = len(self.av)
            v2_detail["authentication"] = {"register_blob": r["authority"].get("register_blob"),
                                           "section_sha256": r["authority"].get("section_sha256"),
                                           "manifest_line": r["authority"].get("manifest_line")}
        self.st["v2_binding"] = v2
        r["v2_binding"] = dict(v2_detail, status=v2)
        # ---------------- full regression (PIW D3-A) ----------------
        fr = "NOT_RUN"
        lf = lanes.get("T-full") or {}
        fr_detail = {}
        if lf and "error" not in lf:
            dsel = lf["deselect"]
            counts = lf["recorder_counts"]
            network = "implementation/" + NETWORK_NODE
            exp_desel = [network] if dsel["valid"] else []
            present = sorted(lf["deselected"])
            other_bad = sorted(n for n, o in lf["outcomes"].items() if o not in ("passed",) and n != network)
            fr_fail = bool(lf["collect_errors"] or other_bad or (lf["junit"] != counts)
                           or (set(lf["collected"]) != set(lf["outcomes"]))
                           or (present != exp_desel and present != [])
                           or (dsel["valid"] and present != exp_desel))
            if fr_fail:
                fr = "FAIL"
            elif not dsel["valid"] and dsel["present_at_T"]:
                fr = "NOT_RUN"          # the network node cannot be excluded: usage error, never PASS
            elif counts["failures"] or counts["errors"] or counts["skipped"]:
                fr = "FAIL"
            else:
                fr = "PASS"
            # Track C nodes must be collected and pass in the shared session
            tc_nodes = set()
            for _, s in (lt.get("pytest") or []):
                tc_nodes |= set(s["collected"])
            for key in ("v2", "ns_extra"):
                if lt.get(key):
                    tc_nodes |= set(lt[key]["collected"])
            missing = sorted(tc_nodes - set(lf["collected"]))
            failing = sorted(n for n in tc_nodes if lf["outcomes"].get(n) not in ("passed",)
                             and n in lf["outcomes"] and lt and self.targeted_outcome(lt, n) == "passed")
            if missing or failing:
                inter_findings.append({"id": "AC-35", "finding": "Track C nodes missing or failing in the full session "
                                       "(cross-test interference)", "missing": missing[:20], "failing": failing[:20]})
            inter_findings += self.plugin_findings(lf, self.lane_dir("T-full"))
            inter_findings += frun.check_trace(lf["result"], self.lane_dir("T-full"), sb.tree(T), allowed,
                                               self.baseline_meta, track_c=False, launcher_dir=self.runner.launch_dir)
            if lf.get("tree_after"):
                inter_findings.append({"id": "AC-31", "finding": "full regression changed the tree",
                                       "problems": [list(p) for p in lf["tree_after"][:10]]})
            fr_detail = {"rc": lf["rc"], "counts": counts, "junit": lf["junit"], "collect_errors": lf["collect_errors"],
                         "deselected": present, "deselect_rule": dsel, "track_c_nodes": len(tc_nodes),
                         "non_track_c_failures": sorted(n for n, o in lf["outcomes"].items()
                                                        if o not in ("passed",) and n not in tc_nodes)[:50]}
        self.st["full_regression"] = fr
        r["full_regression"] = dict(fr_detail, status=fr)
        # trace checks of T Track C sessions and spawns
        spawn_records = []
        if lt and "error" not in lt:
            sessions = [s for _, s in lt["pytest"]] + [lt[k] for k in ("v2", "ns_extra") if lt.get(k)]
            for s in sessions:
                inter_findings += self.plugin_findings(s, lt["root"])
                f, spawns = frun.check_spawns(s["result"], lt["root"], allowed, complement)
                inter_findings += f
                spawn_records += spawns
        if lr and "error" not in lr:
            for _, s in lr["pytest"]:
                inter_findings += self.plugin_findings(s, self.lane_dir("R"))
        # equivalence control at R (AC-29) -> runtime provenance
        lrv = lanes.get("R-verbatim") or {}
        eq = []
        if lr and "error" not in lr and lrv and "error" not in lrv:
            for (st, h), (st2, v) in zip(lr["tools"], lrv["tools"]):
                eq.append({"tool": st["script_path"], "rc_hardened": h.rc, "rc_verbatim": v.rc,
                           "stdout_equal": h.stdout == v.stdout})
            for (st, h), (st2, v) in zip(lr["pytest"], lrv["pytest"]):
                hcases = junit_view(h["outcomes"], h["rootdir"])
                eq.append({"step": st["name"], "rc_hardened": h["rc"], "rc_verbatim": v["rc"],
                           "junit_equal": h["junit"] == v["junit"], "node_outcomes_equal": hcases == (v["cases"] or {}),
                           "nodes": len(hcases)})
        else:
            eq.append({"error": "R lanes unavailable"})
        bad_eq = [e for e in eq if e.get("error") or e.get("rc_hardened") != e.get("rc_verbatim")
                  or e.get("stdout_equal") is False or e.get("junit_equal") is False
                  or e.get("node_outcomes_equal") is False]
        r["runtime_provenance"]["equivalence_control_at_R"] = eq
        if bad_eq and self.st.get("runtime_provenance") == "PASS":
            self.st["runtime_provenance"] = "NOT_RUN"
            r["runtime_provenance"]["status"] = "NOT_RUN"
            r["runtime_provenance"]["checks"].append({"id": "AC-29", "status": "NOT_RUN",
                                                      "detail": "hardened and verbatim runs at R differ (S3)", "items": bad_eq})
        plugin_fail = [f for f in inter_findings if f.get("id") == "AC-28" and f.get("finding") == "unexpected pytest plugin"]
        if plugin_fail:
            self.st["runtime_provenance"] = "FAIL"
            r["runtime_provenance"]["status"] = "FAIL"
        # ---------------- frozen tools on T (AC-32) ----------------
        lfz = lanes.get("T-frozen") or {}
        ft = "NOT_RUN"
        if lfz and "error" not in lfz:
            steps = [s for s in lfz["steps"] if s.get("rc") is not None]
            tools_run = [s for s in steps if s["kind"] == "tool"]
            unknown = [s for s in lfz["steps"] if s.get("deviation") == "unrecognised step; NOT_RUN"]
            if tools_run and not unknown:
                ft = "FROZEN_TOOLS_ON_T_PASS" if all(s["rc"] == 0 for s in steps) else "FROZEN_TOOLS_ON_T_FAIL"
            first = next((s["step"] for s in lfz["steps"] if s.get("rc") not in (None, 0)), None)
            lfz["ci_first_failure"] = first
            lfz["ci_semantics"] = "CI stops at the first failing step; FPIA executes every step to record each verdict"
        self.st["frozen_tools_on_T"] = ft
        r["frozen_tools_on_T"] = dict({k: v for k, v in lfz.items() if k != "error"}, status=ft,
                                      evidence_class="BRANCH_FROZEN_VALIDATION")
        # ---------------- interference status ----------------
        inter_findings = self.dedupe(inter_findings)
        if inter_findings:
            inter = "INTEGRATION_INTERFERENCE_FOUND"
        elif inter_nr or any(k in lane_errors for k in ("T", "T-full")):
            inter = "NOT_RUN"
        else:
            inter = "INTEGRATION_INTERFERENCE_NONE"
        self.st["integration_interference"] = inter
        r["integration_interference"].update({"status": inter, "findings": inter_findings, "not_run": inter_nr,
                                              "targeted_tests": targeted, "reference": ref_name,
                                              "spawns": spawn_records[:50]})

    def site_roots(self):
        return sorted({s["root"] for s in self.sites})

    def targeted_outcome(self, lt, node):
        for _, s in lt.get("pytest", []):
            if node in s["outcomes"]:
                return s["outcomes"][node]
        for key in ("v2", "ns_extra"):
            if lt.get(key) and node in lt[key]["outcomes"]:
                return lt[key]["outcomes"][node]
        return None

    def compare_sessions(self, sT, sRef, complement, allowed, site_list, root, entries):
        findings, not_run = [], []
        rec = {"label": sT["label"], "files": sT["files"], "rootdir_T": sT["rootdir"], "inifile_T": sT["inifile"],
               "collected": len(sT["collected"]), "counts": sT["recorder_counts"], "junit": sT["junit"]}
        if sRef is not None:
            rec.update({"reference": sRef["label"], "rootdir_ref": sRef["rootdir"], "inifile_ref": sRef["inifile"]})
            if sT["files"] != sRef["files"]:
                findings.append({"id": "AC-30", "finding": "test file expansion differs from the reference",
                                 "label": sT["label"]})
            if (sT["rootdir"], sT["inifile"]) != (sRef["rootdir"], sRef["inifile"]):
                findings.append({"id": "AC-27", "finding": "pytest rootdir/inifile determination differs from the reference",
                                 "label": sT["label"], "T": [sT["rootdir"], sT["inifile"]],
                                 "reference": [sRef["rootdir"], sRef["inifile"]]})
            if not reference_clean(sRef):
                not_run.append("reference session %s not clean" % sRef["label"])
            missing = sorted(set(sRef["collected"]) - set(sT["collected"]))
            extra = sorted(set(sT["collected"]) - set(sRef["collected"]))
            if missing or extra:
                findings.append({"id": "AC-30", "finding": "collected node set differs from the reference",
                                 "label": sT["label"], "missing": missing[:20], "extra": extra[:20]})
            diff = sorted(n for n in sRef["outcomes"] if sT["outcomes"].get(n) != sRef["outcomes"][n])
            if diff:
                findings.append({"id": "AC-30", "finding": "per-node outcomes differ from the reference",
                                 "label": sT["label"], "nodes": diff[:20]})
            rec["outcomes_equal"] = not diff
        findings += session_consistency(sT)
        ref_sp = frun.tree_sys_path(sRef["result"], sRef["root"]) if sRef is not None else ()
        findings += frun.check_trace(sT["result"], root, entries, allowed, self.baseline_meta, track_c=True,
                                     reference_sys_path=ref_sp,
                                     complement=complement, sites=site_list, site_roots=self.site_roots(), launcher_dir=self.runner.launch_dir)
        tree_problems = fgit.verify_tree(root, entries, self.out_dirs(root))
        if tree_problems:
            findings.append({"id": "AC-31", "finding": "Track C session changed the tree", "label": sT["label"],
                             "problems": [list(p) for p in tree_problems[:10]]})
        return {"findings": findings, "not_run": not_run, "record": rec}

    def payload_distributions(self, tool_runs):
        used = set()
        try:
            pkgs = __import__("importlib.metadata").metadata.packages_distributions()
        except Exception:
            pkgs = {}
        purelib = {os.path.realpath(p) for p in (__import__("sysconfig").get_paths()["purelib"],
                                                 __import__("sysconfig").get_paths()["platlib"])}
        for st, res in tool_runs:
            trace = res.trace or {}
            startup = set(trace.get("startup_modules", []))
            for name, info in trace.get("modules", {}).items():
                if name in startup or name.split(".")[0] in startup:
                    continue
                origin = info.get("origin")
                if not origin or not os.path.isabs(origin):
                    continue
                real = os.path.realpath(origin)
                if any(real.startswith(p + "/") for p in purelib):
                    for d in pkgs.get(name.split(".")[0], []):
                        used.add(d.lower())
        return used

    def record_claims(self, record, evidence, head):
        problems = []
        values = fd.scalar_values(evidence)
        bdicts = fd.boundary_dicts(evidence, head)
        for k, v in record.items():
            if isinstance(v, str) and (fd.HEX40.match(v) or fd.HEX64.match(v)):
                if v not in values:
                    problems.append({"key": k, "problem": "hex claim not produced by the replay"})
            relational = [b[k] for b in bdicts if k in b and ((isinstance(b[k], int) and not isinstance(b[k], bool))
                                                             or (isinstance(b[k], str) and fd.HEX40.match(b[k])))]
            if not isinstance(v, (dict, list)) and relational:
                if any(x != v for x in relational):
                    problems.append({"key": k, "problem": "boundary claim differs from the replay"})
        return problems

    def log_record_claims(self, rec, data, rp):
        problems = []
        # raw log hash
        logs = rec["logs"]
        sha_claims = [v for _, d in fd.nested_dicts(data) for k, v in d.items() if k.endswith("log_sha256")]
        for lp in logs:
            actual = sha256(self.sb.read(self.R, lp))
            if sha_claims and actual not in sha_claims:
                problems.append({"problem": "raw log sha256 differs", "log": lp})
        if logs and not sha_claims:
            problems.append({"problem": "log referenced without a sha256 binding", "status": "NOT_RUN"})
        by_short = {}
        for t in rp["tools"]:
            short = t["line"].split("=", 1)[0][len("TRACK_C_"):-len("_EVIDENCE")] if t["line"] else None
            if short:
                by_short[short.lower()] = t
        acc = data.get("acceptance")
        if isinstance(acc, dict):
            for k, v in acc.items():
                t = by_short.get(k.lower())
                if t is None:
                    problems.append({"problem": "acceptance key without a replayed tool", "key": k, "status": "NOT_RUN"})
                    continue
                expected = t["evidence"].get("status") if isinstance(t["evidence"], dict) and "status" in t["evidence"] else (
                    "PASS" if t["rc"] == 0 else "FAIL")
                if v != expected:
                    problems.append({"problem": "acceptance value differs from the replay", "key": k})
        last = [t for t in rp["tools"] if t["evidence"] is not None]
        if last:
            ev = last[-1]["evidence"]
            problems += self.record_claims(data, {"_all": [t["evidence"] for t in last]}, rec["head"])
            anywhere = fd.keys_anywhere(ev)
            for k, v in data.items():
                if isinstance(v, bool) and k in anywhere and any(x != v for x in anywhere[k] if isinstance(x, bool)):
                    problems.append({"key": k, "problem": "boolean claim differs from the replay"})
        return problems

    @staticmethod
    def dedupe(items):
        seen, out = set(), []
        for f in items:
            key = json.dumps(f, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                out.append(f)
        return sorted(out, key=lambda f: json.dumps(f, sort_keys=True, default=str))

    # -- output ---------------------------------------------------------------------------------------
    def finish(self):
        r = self.result
        status, reasons = compose(self.st)
        for k in ("historical_frozen_identity", "code_identity", "track_c_projection", "integration_interference",
                  "frozen_tools_on_T", "runtime_provenance", "v2_binding", "full_regression"):
            self.st.setdefault(k, "NOT_RUN")
        r["fpia"] = {"status": status, "reasons": reasons}
        r["options"] = {k: v for k, v in self.opts.items()}
        non_default = sorted(k for k, v in self.opts.items() if DEFAULT_OPTIONS.get(k) != v)
        r["evidence_validity"] = ("CANONICAL_INVOCATION" if not non_default else
                                  "NON_DEFAULT_OPTIONS_NOT_EVIDENCE: " + ",".join(non_default))
        r["summary"] = summary_line(r)
        return r


def junit_view(outcomes, rootdir_rel):
    """Recorder outcomes keyed like junit testcases ("<classname>::<name>")."""
    out = {}
    prefix = (rootdir_rel.rstrip("/") + "/") if rootdir_rel else ""
    for node, outcome in outcomes.items():
        parts = node.split("::")
        module = parts[0][len(prefix):] if parts[0].startswith(prefix) else parts[0]
        module = module[:-3] if module.endswith(".py") else module
        classname = ".".join([module.replace("/", ".")] + parts[1:-1])
        out["%s::%s" % (classname, parts[-1])] = {"failed": "failure", "error": "error", "skipped": "skipped",
                                                   "xfailed": "skipped"}.get(outcome, "passed")
    return out


def verifier_provenance(here, home):
    """FPIA's own files (blob ids), commit and clean-checkout status (review LOW)."""
    here = Path(here)
    files = sorted(p for p in here.iterdir() if p.name.startswith("track_c_fpia") and p.suffix == ".py")
    out = {"files": {p.name: fgit.blob_id(p.read_bytes()) for p in files}}
    env = fgit.base_env(home)
    try:
        top = subprocess.run(["git", "-C", str(here), "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, env=env, check=True).stdout.strip()
        head = subprocess.run(["git", "-C", top, "rev-parse", "HEAD"], capture_output=True, text=True,
                              env=env, check=True).stdout.strip()
        status = subprocess.run(["git", "-C", top, "status", "--porcelain", "--untracked-files=all", "--",
                                 str(here)], capture_output=True, text=True, env=env, check=True).stdout
        out.update({"commit": head, "clean": status.strip() == "", "dirty": status.splitlines()[:20]})
    except (subprocess.CalledProcessError, OSError) as exc:
        out.update({"commit": None, "clean": False, "error": str(exc)[-200:]})
    return out


def session_consistency(sT):
    """Findings for one Track C pytest session on T: deselection, executed vs collected, junit vs
    recorder counts, cleanliness (AC-30)."""
    findings = []
    if sT["deselected"]:
        findings.append({"id": "AC-30", "finding": "tests deselected in a Track C session", "label": sT["label"],
                         "nodes": sT["deselected"][:20]})
    if set(sT["collected"]) != set(sT["outcomes"]):
        findings.append({"id": "AC-30", "finding": "executed node set differs from the collected set",
                         "label": sT["label"]})
    if sT["junit"] != sT["recorder_counts"]:
        findings.append({"id": "AC-30", "finding": "junit counts differ from recorder counts", "label": sT["label"],
                         "junit": sT["junit"], "recorder": sT["recorder_counts"]})
    bad = sorted(n for n, o in sT["outcomes"].items() if o in ("failed", "error"))
    if bad or sT["collect_errors"] or sT["rc"] != 0:
        findings.append({"id": "AC-30", "finding": "Track C session not clean on T", "label": sT["label"],
                         "nodes": bad[:20], "collect_errors": sT["collect_errors"][:10], "rc": sT["rc"]})
    if not sT["collected"]:
        findings.append({"id": "AC-30", "finding": "no tests collected", "label": sT["label"]})
    return findings


def reference_clean(sRef):
    bad = {n: o for n, o in sRef["outcomes"].items() if o in ("failed", "error")}
    return not bad and not sRef["collect_errors"] and sRef["rc"] == 0


def scrub(obj, work):
    w = str(work)
    if isinstance(obj, dict):
        return {k: scrub(v, work) for k, v in obj.items() if not isinstance(v, frun.RunResult)}
    if isinstance(obj, list):
        return [scrub(v, work) for v in obj if not isinstance(v, frun.RunResult)]
    if isinstance(obj, tuple):
        return [scrub(v, work) for v in obj]
    if isinstance(obj, str) and w in obj:
        return obj.replace(w, "<work>")
    if isinstance(obj, (set, frozenset)):
        return sorted(scrub(v, work) for v in obj)
    return obj


def run_fpia(repo, tree, register_commit, cdr, out=None, work_dir=None, keep_work=False, options=None):
    started = time.time()
    created = work_dir is None
    work = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="track-c-fpia-"))
    if not created and work.exists() and any(work.iterdir()):
        raise SystemExit("--work-dir must be empty or new")
    work.mkdir(parents=True, exist_ok=True)
    audit = None
    try:
        audit = Audit(repo, tree, register_commit, cdr, work, options)
        result = audit.run()
    except Exception as exc:  # internal error: NOT_RUN, never PASS
        import traceback
        result = {"schema": SCHEMA, "statuses": {}, "fpia": {"status": "FPIA_NOT_RUN",
                                                             "reasons": ["internal error: %s: %s" % (type(exc).__name__, exc)]},
                  "traceback": traceback.format_exc()[-4000:], "non_claims": NON_CLAIMS}
        result["summary"] = "FPIA_NOT_RUN | internal error"
    result = scrub(result, work.resolve())
    result = json.loads(json.dumps(result, sort_keys=True, default=str))
    doc = {"schema": SCHEMA, "result": result, "result_sha256": sha256(canonical_bytes(result)),
           "run": {"started_utc": datetime.datetime.fromtimestamp(started, datetime.timezone.utc).isoformat(),
                   "duration_s": round(time.time() - started, 1), "work_dir": str(work), "host": platform.node(),
                   "argv": sys.argv, "ref_writes": audit.sb.ref_log if audit else [],
                   "fetches": audit.sb.fetch_log if audit else [], "runs": audit.runner.runs if audit else []}}
    if out:
        Path(out).write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return doc


EXIT = {"FPIA_PASS": 0, "FPIA_FAIL": 1, "FPIA_NOT_RUN": 2}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("usage error: %s\n" % message)
        raise SystemExit(2)


def main(argv=None):
    p = _Parser(description=__doc__.split("\n")[0], allow_abbrev=False)
    p.add_argument("--repo", required=True)
    p.add_argument("--tree", required=True)
    p.add_argument("--register-commit", required=True)
    p.add_argument("--cdr", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--work-dir")
    p.add_argument("--keep-work", action="store_true")
    a = p.parse_args(argv)
    doc = run_fpia(a.repo, a.tree, a.register_commit, a.cdr, out=a.out, work_dir=a.work_dir, keep_work=a.keep_work)
    print(doc["result"].get("summary", doc["result"]["fpia"]["status"]))
    return EXIT[doc["result"]["fpia"]["status"]]


if __name__ == "__main__":
    sys.exit(main())
