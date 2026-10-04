"""Provenance per commit and per merge (AC-20; CDR-014 §5, §8, §9; review HIGH #2)."""
from tests import integration_fpia_testkit as tk

EVL = "implementation/src/investment_system/evl/"


def prov(a):
    return [c for c in a.provenance_checks if c["status"] != "PASS"]


def audit(w, T):
    return w.audit(T, w.register(w.c["R0"], [w.c["V0"]], [T]))


def test_foreign_edit_then_revert_fails(tmp_path):
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    p = "implementation/tests/test_evl_c6_basic.py"
    t1 = g.change(T, {p: g.read(T, p).decode() + "\n# foreign edit\n"}, "foreign edit")
    t2 = g.change(t1, {p: g.read(T, p)}, "foreign revert")
    a = audit(w, t2)
    assert not [c for c in a.projection_checks if c["status"] != "PASS"]      # bytes are identical again
    assert any(c["id"] == "AC-20" and "non-merge" in c["detail"] for c in prov(a))


def test_foreign_register_append_discarded_at_merge_fails(tmp_path):
    w = tk.variant(tmp_path)
    g, V, F = w.git, w.c["V0"], w.c["F"]
    side = g.change(F, {tk.DR: "# foreign register\n"}, "foreign register file on the foreign branch")
    T = g.merge(V, side, "merge discarding the foreign register", resolve={tk.DR: g.read(V, tk.DR)})
    a = audit(w, T)
    assert prov(a)


def test_evil_merge_fails(tmp_path):
    w = tk.variant(tmp_path)
    g, V, F = w.git, w.c["V0"], w.c["F"]
    T = g.merge(V, F, "evil merge", resolve={EVL + "x.py": "EVIL = 1\n"})
    a = audit(w, T)
    assert any(c["id"] == "AC-20" for c in prov(a)) or any(f["id"] == "AC-21" for f in a.static_findings)


def test_overlay_conflict_resolution_fails(tmp_path):
    w = tk.variant(tmp_path)
    g, K, V = w.git, w.c["K"], w.c["V0"]
    overlay = tk.ROOT_OVERLAYS[0]
    X = g.change(K, {overlay: g.read(K, overlay).decode() + "- X entry\n"}, "X")
    T = g.merge(X, V, "merge", resolve={overlay: g.read(V, overlay).decode() + "- X entry\n"})
    a = audit(w, T)
    assert a.ref_status == "PASS"
    assert any(c["id"] == "AC-20" and "conflict" in c["detail"] for c in prov(a))


def test_merge_drop_and_restore_via_stale_parent_fails(tmp_path):
    """Review demo_c: M1 = merge(V-side, F) resolved to F's stale p; M2 = merge(M1, B) resolved back.
    Final p equals the authenticated bytes, no non-merge commit outside L touches p and
    ``git diff-tree -c`` lists nothing, yet the clean recomputation of M1 differs -> FAIL."""
    w = tk.variant(tmp_path)
    g, V = w.git, w.c["V0"]
    p = tk.WORKFLOW                      # protected; changed on the Track C lineage after S6
    F = g.change(w.c["S6"], {"implementation/docs/side.md": "side\n"}, "F forked before p changed")
    M1 = g.merge(V, F, "M1 resolves p to the stale parent", resolve={p: g.read(F, p)})
    B = g.change(V, {"implementation/docs/b.md": "b\n"}, "B forked from V")
    M2 = g.merge(M1, B, "M2 restores p", resolve={p: g.read(V, p)})
    assert g.read(M2, p) == g.read(V, p)
    assert g("diff-tree", "-r", "-c", "--name-only", M1) .find(p) < 0
    a = audit(w, M2)
    assert not [c for c in a.projection_checks if c["status"] != "PASS" and c.get("path") == p]
    assert any(c["id"] == "AC-20" and M1 in str(c) for c in prov(a)), a.provenance_checks


def test_merge_drop_and_restore_on_shared_overlay_fails(tmp_path):
    w = tk.variant(tmp_path)
    g, K, V = w.git, w.c["K"], w.c["V0"]
    overlay = tk.ROOT_OVERLAYS[1]
    stale = g.change(K, {"implementation/docs/side.md": "side\n"}, "stale side from K")
    M1 = g.merge(V, stale, "M1 picks K's overlay", resolve={overlay: g.read(K, overlay)})
    B = g.change(V, {"implementation/docs/b.md": "b\n"}, "B")
    M2 = g.merge(M1, B, "M2 restores", resolve={overlay: g.read(V, overlay)})
    a = audit(w, M2)
    assert any(c["id"] == "AC-20" for c in prov(a)), a.provenance_checks


def test_clean_merge_combining_authenticated_sides_passes(tmp_path):
    """The 5d0a49b pattern: a clean merge whose projection content all comes from V's lineage."""
    w = tk.variant(tmp_path)
    g, V, F = w.git, w.c["V0"], w.c["F"]
    Fx = g.change(F, {"implementation/docs/foreign.md": "f\n"}, "foreign work")
    M = g.merge(Fx, V, "foreign branch merges the v2 head (projection from parent 2)")
    a = audit(w, M)
    assert a.ref_status == "PASS"
    assert not prov(a)
    assert w.c["T0"] != M and a.result["track_c_projection"]["provenance"]["merges"] >= 1


def test_foreign_only_conflict_ignored(tmp_path):
    """The 4ccdd3a pattern: a manually resolved conflict in a non-projection file does not fail."""
    w = tk.variant(tmp_path)
    g, V, F = w.git, w.c["V0"], w.c["F"]
    app = "implementation/web_assets/app.js"
    F1 = g.change(F, {app: "a\n"}, "foreign app a")
    V1 = g.change(V, {app: "b\n"}, "other app b")
    T = g.merge(V1, F1, "manual resolution", resolve={app: "ab\n"})
    a = w.audit(T, w.register(w.c["R0"], [w.c["V0"]], [T]))
    assert not [c for c in prov(a) if app in str(c)]


def test_octopus_not_run(tmp_path):
    w = tk.variant(tmp_path)
    g, V, F = w.git, w.c["V0"], w.c["F"]
    other = g.change(w.c["K"], {"implementation/docs/o.md": "o\n"}, "other")
    files = dict(g.files(V))
    files.update(g.files(F))
    files.update(g.files(other))
    files[tk.DR] = ("100644", g.blob(g.read(V, tk.DR) + b"octopus\n"))
    T = g.commit(g.tree(files), [V, F, other], "octopus")
    a = audit(w, T)
    assert any(c["status"] == "NOT_RUN" and "octopus" in c["detail"] for c in a.provenance_checks)
