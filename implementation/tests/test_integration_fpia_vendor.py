"""The FPIA workflow loader is the vendored pure-Python PyYAML 6.0.1 (tools/integration/_vendor/README.md).

The owner full-suite workflows install only pytest and numpy, so the FPIA must not depend on an installed
PyYAML. These tests pin the vendored files to the upstream sdist digests recorded in the README, and check
that the loader in use is the vendored copy without libyaml, whatever PyYAML (if any) is installed.
"""
import hashlib
import re
import subprocess
import sys

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia_workflows as fw

VENDOR = tk.REPO_ROOT / "implementation" / "tools" / "integration" / "_vendor"
UPSTREAM_SDIST_SHA256 = "bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43"


def _readme_digests():
    text = (VENDOR / "README.md").read_text()
    assert UPSTREAM_SDIST_SHA256 in text
    return {name: digest for digest, name in re.findall(r"^([0-9a-f]{64})  (\S+)$", text, re.M)}


def test_vendored_files_match_recorded_upstream_digests():
    digests = _readme_digests()
    on_disk = sorted(p.name for p in (VENDOR / "yaml").iterdir() if p.name != "__pycache__")
    assert on_disk == sorted(digests)
    assert "cyaml.py" not in digests and "LICENSE" in digests and "__init__.py" in digests
    for name, digest in digests.items():
        assert hashlib.sha256((VENDOR / "yaml" / name).read_bytes()).hexdigest() == digest, name


def test_no_compiled_or_bytecode_files_committed_under_vendor():
    out = subprocess.run(["git", "ls-files", "--", str(VENDOR)], cwd=tk.REPO_ROOT, capture_output=True,
                         text=True, check=True).stdout.split()
    assert out, "vendored files are not tracked"
    assert not [p for p in out if p.endswith((".pyc", ".pyo", ".so", ".pyd")) or "__pycache__" in p]


def test_loader_is_the_vendored_copy_without_libyaml():
    assert fw.yaml is not None
    assert fw.yaml.__name__.endswith("_vendor.yaml")
    assert fw.yaml.__file__.startswith(str(VENDOR))
    assert fw.yaml.__version__ == "6.0.1" and fw.yaml.__with_libyaml__ is False
    info = fw.loader_info()
    assert info["version"] == "6.0.1" and info["source"].startswith("vendored") and info["with_libyaml"] is False


def test_script_mode_import_uses_the_vendored_copy():
    """``python track_c_fpia.py`` (as the CI audit step runs it) loads _vendor/yaml with -s and no PYTHONPATH."""
    code = ("import track_c_fpia_workflows as fw; import sys; "
            "print(fw.yaml.__name__, fw.yaml.__file__, fw.yaml.__with_libyaml__)")
    tools = VENDOR.parent
    res = subprocess.run([sys.executable, "-E", "-s", "-B", "-c", "import sys; sys.path.insert(0, %r); %s" % (str(tools), code)],
                         capture_output=True, text=True, cwd=str(tools))
    assert res.returncode == 0, res.stderr
    name, path, libyaml = res.stdout.split()
    assert name == "_vendor.yaml" and path.startswith(str(VENDOR)) and libyaml == "False"
