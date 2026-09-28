"""CLI: python -m validation [--verbose]. Exit code 1 on any failure."""

import sys

from validation import fixture_runner, metamorphic


def main(argv: list[str]) -> int:
    verbose = "--verbose" in argv
    failures = 0

    print("== Fixtures ==")
    for result in fixture_runner.run_all():
        status = "PASS" if result.passed else "FAIL"
        failures += not result.passed
        print(f"{status}  {result.fixture_id:<12} {result.kind:<14} {result.title}")
        for mismatch in result.mismatches:
            print(f"        - {mismatch}")
        if verbose:
            for change in result.changed_from_base:
                print(f"        ~ {change}")

    print("== Metamorphic relations ==")
    for result in metamorphic.run_all():
        status = "PASS" if result.passed else "FAIL"
        failures += not result.passed
        print(f"{status}  {result.relation_id:<6} {result.kind:<8} checks={result.checked:<6} {result.title}")
        for violation in result.violations[: metamorphic.MAX_EXAMPLES]:
            print(f"        - {violation}")
        if len(result.violations) > metamorphic.MAX_EXAMPLES:
            print(f"        ... {len(result.violations) - metamorphic.MAX_EXAMPLES} more")

    print(f"== {'FAILED' if failures else 'ALL PASS'} ({failures} failing) ==")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
