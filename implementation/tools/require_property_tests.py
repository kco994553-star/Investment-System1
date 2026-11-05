"""Fail a required CI job when the technical property tests did not really run (owner 2026-11-05, #489 hand-over).

tests/research/test_technical_properties.py skips its whole module when Hypothesis is missing (pytest.importorskip), and a
skip is green. In the required build job that green would read as "properties verified" when nothing was generated. This
check turns that into a named failure:

  - every pin in tests/research/dependencies/technical-properties.txt is installed at exactly that version
    (else PROPERTY_DEPENDENCY_MISSING / PROPERTY_DEPENDENCY_VERSION);
  - the pytest JUnit report of the property run has no skip, failure or error (else PROPERTY_TESTS_SKIPPED / _FAILED);
  - every test function defined in the property module is in the report and passed (else PROPERTY_TESTS_MISSING), so a
    renamed or deleted module cannot pass by running nothing.

Usage (implementation/):  python tools/require_property_tests.py <junit.xml>
Output is one fixed line per outcome with counts only. Main owns this file and the workflow step; the tests are Codex's.
"""
from __future__ import annotations

import ast
import sys
import xml.etree.ElementTree as ET
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'tests/research/dependencies/technical-properties.txt'
MODULE = ROOT / 'tests/research/test_technical_properties.py'
MODULE_CLASS = 'tests.research.test_technical_properties'


def pins(path: Path = REQUIREMENTS) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        name, sep, version = line.partition('==')
        if not sep or not name.strip() or not version.strip():
            raise ValueError('PROPERTY_PIN_NOT_EXACT')
        out[name.strip().lower()] = version.strip()
    if not out:
        raise ValueError('PROPERTY_PIN_EMPTY')
    return out


def check_installed(required: dict[str, str], version_of=metadata.version) -> str | None:
    for name, want in sorted(required.items()):
        try:
            got = version_of(name)
        except metadata.PackageNotFoundError:
            return 'PROPERTY_DEPENDENCY_MISSING ' + name
        if got != want:
            return 'PROPERTY_DEPENDENCY_VERSION ' + name
    return None


def module_tests(path: Path = MODULE) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_')}


def check_report(xml_text: str, expected: set[str], classname: str = MODULE_CLASS) -> tuple[str | None, dict[str, int]]:
    root = ET.fromstring(xml_text)
    cases = list(root.iter('testcase'))
    counts = {'tests': len(cases), 'skipped': 0, 'failed': 0, 'property_passed': 0}
    passed_props = set()
    for case in cases:
        kids = {child.tag for child in case}
        if 'skipped' in kids:
            counts['skipped'] += 1
        elif kids & {'failure', 'error'}:
            counts['failed'] += 1
        elif case.get('classname') == classname:
            passed_props.add(case.get('name', '').split('[', 1)[0])
    counts['property_passed'] = len(passed_props & expected)
    if counts['skipped']:
        return 'PROPERTY_TESTS_SKIPPED', counts
    if counts['failed']:
        return 'PROPERTY_TESTS_FAILED', counts
    if not expected or not expected <= passed_props:
        return 'PROPERTY_TESTS_MISSING', counts
    return None, counts


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('PROPERTY_CHECK_USAGE')
        return 2
    try:
        problem = check_installed(pins())
        if problem is None:
            problem, counts = check_report(Path(argv[1]).read_text(encoding='utf-8'), module_tests())
        else:
            counts = None
    except (OSError, ValueError, SyntaxError, ET.ParseError) as exc:
        print('PROPERTY_CHECK_UNREADABLE ' + type(exc).__name__)
        return 1
    if problem:
        print(problem + ('' if counts is None else ' ' + ' '.join(f'{k}={v}' for k, v in counts.items())))
        return 1
    print('PROPERTY_TESTS_RAN ' + ' '.join(f'{k}={v}' for k, v in counts.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
