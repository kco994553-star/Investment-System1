"""The flow quality test's axe rule scan is required in the cockpit-pages build (owner 2026-11-05, #494)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / '.github/workflows/cockpit-pages.yml'
TEST = ROOT / 'implementation/tools/web_app_flow_quality_browser_test.js'
LIST = ROOT / 'implementation/tools/ci_browser_tests.txt'


def build_step():
    text = PAGES.read_text(encoding='utf-8')
    build = text.split('\n  build:\n', 1)[1].split('\n  deploy:\n', 1)[0]
    return build.split('- name: Verify device features and price-free pages locally\n', 1)[1].split('\n      - name: ', 1)[0]


def test_build_installs_pinned_axe_without_scripts_and_requires_it():
    step = build_step()
    assert '          AXE_CORE_PATH: ${{ runner.temp }}/axe/node_modules/axe-core/axe.min.js\n' in step
    assert "          QUALITY_REQUIRE_AXE: '1'\n" in step
    install = 'npm install --ignore-scripts --no-audit --no-fund --prefix "$RUNNER_TEMP/axe" axe-core@4.14.0\n'
    assert install in step
    assert step.index(install) < step.index('bash implementation/tools/run_js_tests.sh implementation/tools/ci_browser_tests.txt')


def test_flow_quality_test_is_listed_and_refuses_a_skip_or_another_build():
    assert 'web_app_flow_quality_browser_test.js' in LIST.read_text(encoding='utf-8')
    src = TEST.read_text(encoding='utf-8')
    assert re.search(r"const AXE_SHA256 = '[0-9a-f]{64}';", src)
    assert "if (!AXE) throw new Error('AXE_NOT_AVAILABLE" in src and "throw new Error('AXE_BUILD_UNEXPECTED" in src
    assert "process.env.QUALITY_REQUIRE_AXE === '1'" in src
