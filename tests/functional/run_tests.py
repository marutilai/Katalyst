import argparse
from tests.functional.test_framework import KatalystTestRunner
from tests.functional.test_suite import (
    basic_tests,
    search_read_tests,
    code_analysis_tests,
    diff_syntax_tests,
    command_tests,
    complex_tests,
)
import sys


def main():
    parser = argparse.ArgumentParser(description="Run Katalyst test suites")
    parser.add_argument(
        "--suite",
        choices=["basic", "search", "code", "diff", "command", "complex", "all"],
        default="all",
        help="Test suite to run",
    )
    parser.add_argument(
        "--report", default="test_report.json", help="Output file for test report"
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all user interactions (use with caution)",
    )

    args = parser.parse_args()

    # Select test suite
    if args.suite == "basic":
        tests = basic_tests
    elif args.suite == "search":
        tests = search_read_tests
    elif args.suite == "code":
        tests = code_analysis_tests
    elif args.suite == "diff":
        tests = diff_syntax_tests
    elif args.suite == "command":
        tests = command_tests
    elif args.suite == "complex":
        tests = complex_tests
    else:  # all
        tests = (
            basic_tests
            + search_read_tests
            + code_analysis_tests
            + diff_syntax_tests
            + command_tests
            + complex_tests
        )

    # Override auto_approve if specified
    if args.auto_approve:
        for test in tests:
            test.auto_approve = True

    # Run tests
    runner = KatalystTestRunner(auto_approve=True)
    results = runner.run_tests(tests)
    runner.generate_report(results)

    # Print summary
    passed = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    print(f"\nTest Summary: {passed} passed, {failed} failed, {len(results)} total.")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
