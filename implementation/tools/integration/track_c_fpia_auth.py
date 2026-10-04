"""FPIA reference authentication (CDR-014 §4).

R (Track C reference) and V (v2 reference) come ONLY from the ``fpia-reference-manifest`` block of
the selected CDR section in the coordination register at the register commit G. A reference is
accepted only if its quoted form occurs as a delimited token in that section's user-verbatim
(``>``) lines, resolves to the manifest SHA, G is an ancestor of the handoff branch tip obtained
from the authority remote (never from the caller's repository), and the register at G is a byte
prefix of the register at that tip. A later manifest naming different references makes
authentication NOT_RUN (no supersession inference).
"""
from __future__ import annotations

import hashlib
import json
import re

try:
    from . import track_c_fpia_git as fgit
except ImportError:
    import track_c_fpia_git as fgit

REGISTER_PATH = "implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md"
HANDOFF_BRANCH = "integration/global-handoff-v1"
AUTHORITY_REMOTE = "https://github.com/kco994553-star/Investment-System1"
FENCE = "fpia-reference-manifest"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class AuthResult(dict):
    status = property(lambda self: self["status"])


def _sections(text):
    lines = text.split("\n")
    heads = [(i, line) for i, line in enumerate(lines) if line.startswith("## ")]
    out = []
    for k, (i, line) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        token = line[3:].split()[0] if line[3:].split() else ""
        out.append({"cdr": token, "start": i, "end": end})
    return lines, out


def _blocks(lines):
    blocks = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "```" + FENCE:
            j = i + 1
            while j < len(lines) and lines[j].strip() != "```":
                j += 1
            blocks.append({"start": i, "end": j, "text": "\n".join(lines[i + 1:j]), "closed": j < len(lines)})
            i = j + 1
        else:
            i += 1
    return blocks


def _refs(manifest):
    out = []
    tc = manifest.get("track_c_reference")
    out.append(("track_c", tc))
    v2 = manifest.get("v2_reference")
    if isinstance(v2, list):
        out.extend(("v2", v) for v in v2)
    elif v2 is not None:
        out.append(("v2", v2))
    return out


def parse_manifest(text, cdr):
    """Returns (manifest, section, verbatim_lines, checks) from register text."""
    checks = []
    lines, sections = _sections(text)
    selected = [s for s in sections if s["cdr"] == cdr]
    if len(selected) != 1:
        checks.append({"id": "AC-02", "status": "FAIL", "detail": "expected exactly one '## %s' section, found %d"
                       % (cdr, len(selected))})
        return None, None, None, checks
    sec = selected[0]
    blocks = _blocks(lines)
    inside = [b for b in blocks if sec["start"] < b["start"] < sec["end"]]
    if len(inside) != 1:
        checks.append({"id": "AC-02", "status": "FAIL", "detail": "expected exactly one manifest block in the "
                       "section, found %d" % len(inside)})
        return None, sec, None, checks
    block = inside[0]
    if not block["closed"]:
        checks.append({"id": "AC-02", "status": "FAIL", "detail": "unterminated manifest block"})
        return None, sec, None, checks
    try:
        manifest = json.loads(block["text"])
    except ValueError as exc:
        checks.append({"id": "AC-02", "status": "FAIL", "detail": "manifest JSON invalid: %s" % exc})
        return None, sec, None, checks
    if not isinstance(manifest, dict) or manifest.get("cdr") != cdr:
        checks.append({"id": "AC-02", "status": "FAIL", "detail": "manifest cdr field does not equal --cdr"})
        return None, sec, None, checks
    for b in blocks:
        if b is block:
            continue
        try:
            other = json.loads(b["text"])
        except ValueError:
            continue
        if isinstance(other, dict) and other.get("cdr") == cdr:
            checks.append({"id": "AC-02", "status": "FAIL", "detail": "another manifest block names the same cdr",
                           "line": b["start"] + 1})
            return None, sec, None, checks
    verbatim = [(i + 1, lines[i]) for i in range(sec["start"], sec["end"]) if lines[i].startswith(">")]
    sec = dict(sec, block_line=block["start"] + 1, text="\n".join(lines[sec["start"]:sec["end"]]))
    return manifest, sec, verbatim, checks


def later_manifests(text, cdr, after_line, selected_refs):
    """Manifests appearing after the selected block whose references differ (NOT_RUN trigger)."""
    lines, sections = _sections(text)
    out = []
    for b in _blocks(lines):
        if b["start"] + 1 <= after_line:
            continue
        try:
            m = json.loads(b["text"])
        except ValueError:
            out.append({"line": b["start"] + 1, "problem": "unparseable later manifest"})
            continue
        refs = sorted((k, (v or {}).get("sha")) for k, v in _refs(m) if isinstance(v, dict) or v is None)
        if refs != selected_refs:
            out.append({"line": b["start"] + 1, "cdr": m.get("cdr"), "references": refs})
    return out


def authenticate(sb, register_commit, cdr, fetch_refs, authority_remote=AUTHORITY_REMOTE):
    """Authenticate R and V. ``fetch_refs(shas)`` makes reference commits available in the sandbox.

    Returns AuthResult with status PASS/FAIL/NOT_RUN, R, Vs, checks and provenance details."""
    res = AuthResult(status="NOT_RUN", cdr=cdr, register_commit=register_commit, register_path=REGISTER_PATH,
                     handoff_branch=HANDOFF_BRANCH, checks=[],
                     remote={"url": authority_remote, "default": authority_remote == AUTHORITY_REMOTE})
    checks = res["checks"]

    def fail(cid, detail, status="FAIL", **extra):
        checks.append(dict({"id": cid, "status": status, "detail": detail}, **extra))
        res["status"] = status

    if not HEX40.match(register_commit or ""):
        fail("AC-01", "--register-commit must be a full 40-hex commit id", "NOT_RUN")
        return res
    # 1. handoff tip from the authority remote (never from the caller's repository)
    try:
        sb.fetch(authority_remote, ["+refs/heads/%s:refs/fpia/authority/handoff-tip" % HANDOFF_BRANCH],
                 network=authority_remote.startswith(("https://", "http://", "ssh://", "git://")),
                 label="authority-remote")
        tip = sb.commit("refs/fpia/authority/handoff-tip")
    except fgit.GitError as exc:
        fail("AC-03", "handoff tip unavailable from the authority remote: %s" % str(exc)[-300:], "NOT_RUN")
        return res
    res["handoff_tip"] = tip
    try:
        sb.commit(register_commit)
    except fgit.GitError:
        fail("AC-03", "register commit not present in the sandbox", "NOT_RUN")
        return res
    if not sb.is_ancestor(register_commit, tip):
        fail("AC-03", "register commit is not an ancestor of the authority handoff tip")
        return res
    reg_g, reg_tip = sb.read(register_commit, REGISTER_PATH), sb.read(tip, REGISTER_PATH)
    if reg_g is None or reg_tip is None:
        fail("AC-03", "register missing at the register commit or at the handoff tip")
        return res
    res["register_blob"] = fgit.blob_id(reg_g)
    res["register_tip_blob"] = fgit.blob_id(reg_tip)
    if not reg_tip.startswith(reg_g):
        fail("AC-03", "register at the register commit is not a byte prefix of the register at the tip")
        return res
    checks.append({"id": "AC-03", "status": "PASS", "detail": "ancestor of authority tip; register prefix holds"})
    # 2. manifest
    text = reg_g.decode("utf-8")
    manifest, sec, verbatim, mchecks = parse_manifest(text, cdr)
    checks.extend(mchecks)
    if manifest is None:
        res["status"] = "FAIL"
        return res
    res["manifest"] = manifest
    res["section_sha256"] = hashlib.sha256(sec["text"].encode()).hexdigest()
    res["section_line"] = sec["start"] + 1
    res["manifest_line"] = sec["block_line"]
    refs = _refs(manifest)
    tc = [v for k, v in refs if k == "track_c"]
    if not tc or not isinstance(tc[0], dict):
        fail("AC-01", "manifest has no track_c_reference", "NOT_RUN")
        return res
    resolved = {}
    shas = []
    for kind, ref in refs:
        if not isinstance(ref, dict) or not HEX40.match(str(ref.get("sha", ""))) \
                or not isinstance(ref.get("quoted_as"), str) or not ref["quoted_as"] \
                or not ref["sha"].startswith(ref["quoted_as"].lower()):
            fail("AC-02", "malformed reference or quoted_as not a prefix of sha", kind=kind)
            res["status"] = "FAIL"
            return res
        shas.append(ref["sha"])
    try:
        fetch_refs(shas)
    except fgit.GitError as exc:
        fail("AC-02", "reference commits unavailable: %s" % str(exc)[-300:], "NOT_RUN")
        return res
    for kind, ref in refs:
        q = ref["quoted_as"]
        rx = re.compile(r"(?<![0-9a-fA-F])" + re.escape(q) + r"(?![0-9a-fA-F])")
        lines = [n for n, line in verbatim if rx.search(line)]
        if not lines:
            fail("AC-02", "quoted reference not found as a delimited token in the user-verbatim lines",
                 kind=kind, quoted_as=q)
            res["status"] = "FAIL"
            return res
        proc = sb.run(["rev-parse", "--verify", "--quiet", q + "^{commit}"], check=False)
        got = proc.stdout.decode().strip()
        if proc.returncode != 0 or got != ref["sha"]:
            fail("AC-02", "quoted reference does not resolve uniquely to the manifest sha", kind=kind, quoted_as=q)
            res["status"] = "FAIL"
            return res
        resolved.setdefault(kind, []).append({"sha": ref["sha"], "quoted_as": q, "verbatim_lines": lines,
                                              "role": ref.get("role")})
    checks.append({"id": "AC-02", "status": "PASS", "detail": "references authenticated from user-verbatim lines"})
    selected = sorted((k, v.get("sha")) for k, v in refs)
    later = later_manifests(reg_tip.decode("utf-8", "replace"), cdr, sec["block_line"], selected)
    res["later_manifests"] = later
    if later:
        fail("AC-03", "a later manifest at the authority tip names different references", "NOT_RUN")
        return res
    res["R"] = resolved["track_c"][0]["sha"]
    res["Vs"] = [v["sha"] for v in resolved.get("v2", [])]
    res["references"] = resolved
    res["verification_subjects"] = manifest.get("verification_subjects")
    res["status"] = "PASS"
    return res


def dr_linkage(sb, R, V, G, dr_path, register_dir):
    """AC-17 (review LOW): attribute V's register appends to introducing commits in R..V and locate
    the authenticating evidence at G (external premise)."""
    rb, vb = sb.read(R, dr_path), sb.read(V, dr_path)
    if rb is None or vb is None or not vb.startswith(rb):
        return {"status": "NOT_RUN", "detail": "register not an append at V"}
    appended = vb[len(rb):].decode("utf-8", "replace")
    sections = []
    cur = []
    for line in appended.split("\n"):
        if line.startswith("## ") and cur:
            sections.append("\n".join(cur))
            cur = []
        cur.append(line)
    if cur:
        sections.append("\n".join(cur))
    sections = [s for s in sections if s.strip()]
    commits = sb.rev_list("--reverse", "--topo-order", V, "--not", R, "--", dr_path)
    attribution = []
    for s in sections:
        intro = None
        for c in commits:
            data = sb.read(c, dr_path) or b""
            ps = sb.parents(c)
            prior = [sb.read(p, dr_path) or b"" for p in ps]
            if s.encode() in data and not any(s.encode() in x for x in prior):
                intro = c
                break
        attribution.append({"section_head": s.split("\n", 1)[0][:120], "sha256": hashlib.sha256(s.encode()).hexdigest(),
                            "introduced_by": intro})
    evidence = []
    tree = sb.tree(G)
    for p, e in sorted(tree.items()):
        if p.startswith(register_dir + "/evidence/") and e.type == "blob":
            data = sb.blob(e.sha)
            if V.encode() in data:
                evidence.append({"path": p, "blob": e.sha})
    status = "PASS" if all(a["introduced_by"] for a in attribution) and evidence else "NOT_RUN"
    return {"status": status, "sections": attribution, "authenticating_evidence_at_G": evidence,
            "premise": "EXTERNAL_PREMISE: 'no approval-boundary expansion' of V's register appends is certified "
                       "by the authenticated v2 verification evidence at G, not by FPIA parsing"}
