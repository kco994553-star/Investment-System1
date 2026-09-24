"""Minimal offline test runner. NOT pytest.

Why: this sandbox has no network and no pytest wheel. The suite only uses
pytest.approx / pytest.raises / tmp_path / monkeypatch.delenv|setenv, so a
small shim runs the same test functions unchanged. Evidence produced with this
runner is recorded as "mini_pytest shim", never as a pytest run.

Usage: python tools/mini_pytest.py [tests/test_x.py ...]
"""

from __future__ import annotations

import importlib.util
import inspect
import math
import os
import sys
import tempfile
import time
import traceback
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class _Approx:
    def __init__(self, expected, rel=1e-6, abs=1e-12):
        self.expected, self.rel, self.abs = expected, rel, abs

    def __eq__(self, other):
        return math.isclose(other, self.expected, rel_tol=self.rel, abs_tol=self.abs)

    def __repr__(self):
        return f"approx({self.expected})"


class _Raises:
    def __init__(self, exc, match=None):
        self.exc, self.match = exc, match

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            raise AssertionError(f"DID NOT RAISE {self.exc}")
        if not issubclass(et, self.exc):
            return False
        if self.match:
            import re
            assert re.search(self.match, str(ev)), f"{ev!r} !~ {self.match}"
        self.value = ev
        return True


class MonkeyPatch:
    def __init__(self):
        self._env: list[tuple[str, str | None]] = []
        self._attrs: list[tuple[object, str, object]] = []

    def setenv(self, k, v):
        self._env.append((k, os.environ.get(k)))
        os.environ[k] = str(v)

    def delenv(self, k, raising=True):
        if k not in os.environ and raising:
            raise KeyError(k)
        self._env.append((k, os.environ.get(k)))
        os.environ.pop(k, None)

    def setattr(self, target, name_or_value, value=None):
        # pytest's monkeypatch.setattr supports both (obj, name, value) and the
        # dotted-string form ("module.attr", value); real code (and tests
        # written against real pytest) may use either.
        if value is None and isinstance(target, str):
            path, _, attr = target.rpartition(".")
            import importlib
            obj = importlib.import_module(path)
            name, value = attr, name_or_value
        else:
            obj, name, value = target, name_or_value, value
        self._attrs.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        for k, v in reversed(self._env):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for obj, name, v in reversed(self._attrs):
            setattr(obj, name, v)


def _install_shim():
    mod = types.ModuleType("pytest")
    mod.approx = _Approx
    mod.raises = _Raises
    mod.MonkeyPatch = MonkeyPatch
    sys.modules["pytest"] = mod


def run(paths: list[Path]) -> int:
    _install_shim()
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    passed, failed = 0, []
    t0 = time.perf_counter()
    for p in paths:
        name = "tests." + p.stem
        spec = importlib.util.spec_from_file_location(name, p)
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        try:
            spec.loader.exec_module(m)
        except Exception:
            failed.append((f"{p.name}::<import>", traceback.format_exc()))
            continue
        for fname, fn in inspect.getmembers(m, inspect.isfunction):
            if not fname.startswith("test_") or fn.__module__ != name:
                continue
            kwargs, mp = {}, MonkeyPatch()
            params = inspect.signature(fn).parameters
            tmp = None
            if "tmp_path" in params:
                tmp = tempfile.TemporaryDirectory()
                kwargs["tmp_path"] = Path(tmp.name)
            if "monkeypatch" in params:
                kwargs["monkeypatch"] = mp
            try:
                fn(**kwargs)
                passed += 1
            except Exception:
                failed.append((f"{p.name}::{fname}", traceback.format_exc()))
            finally:
                mp.undo()
                if tmp:
                    tmp.cleanup()
    dt = time.perf_counter() - t0
    for n, tb in failed:
        print(f"FAILED {n}\n{tb}")
    print(f"{passed} passed, {len(failed)} failed in {dt:.2f}s (runner: mini_pytest shim, not pytest)")
    return 1 if failed else 0


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "tests").glob("test_*.py"))
    sys.exit(run([a.resolve() for a in args]))
