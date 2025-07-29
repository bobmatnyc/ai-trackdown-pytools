#!/usr/bin/env python3
"""Comprehensive CLI test runner for ai-trackdown-pytools."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def run_cli_tests(
    test_types: Optional[List[str]] = None,
    verbose: bool = False,
    coverage: bool = False,
    parallel: bool = False,
    markers: Optional[List[str]] = None,
    output_format: str = "text",
) -> int:
    """Run CLI tests with specified options.

    Args:
        test_types: Types of tests to run (options, interactive, e2e, formats, errors)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        parallel: Run tests in parallel
        markers: Pytest markers to include/exclude
        output_format: Output format (text, json, xml, html)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """

    # Build pytest arguments
    pytest_args = []

    # Determine test files to run
    test_dir = Path(__file__).parent

    if test_types:
        test_files = []
        for test_type in test_types:
            if test_type == "options":
                test_files.append(str(test_dir / "test_comprehensive_cli_options.py"))
            elif test_type == "interactive":
                test_files.append(str(test_dir / "test_interactive_prompts.py"))
            elif test_type == "e2e":
                test_files.append(str(test_dir / "test_e2e_ticket_lifecycle.py"))
            elif test_type == "formats":
                test_files.append(str(test_dir / "test_output_formats_errors.py"))
            elif test_type == "errors":
                test_files.append(
                    str(test_dir / "test_output_formats_errors.py::TestErrorConditions")
                )
            elif test_type == "all":
                test_files = [str(test_dir)]
                break

        if test_files:
            pytest_args.extend(test_files)
    else:
        # Run all CLI tests by default
        pytest_args.append(str(test_dir))

    # Verbose output
    if verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")

    # Coverage reporting
    if coverage:
        pytest_args.extend(
            [
                "--cov=ai_trackdown_pytools",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/cli_coverage",
                "--cov-report=xml:coverage_cli.xml",
            ]
        )

    # Parallel execution
    if parallel:
        pytest_args.extend(["-n", "auto"])

    # Markers
    if markers:
        for marker in markers:
            if marker.startswith("not "):
                pytest_args.extend(["-m", marker])
            else:
                pytest_args.extend(["-m", marker])

    # Output format
    if output_format == "json":
        pytest_args.extend(["--json-report", "--json-report-file=test_report_cli.json"])
    elif output_format == "xml":
        pytest_args.extend(["--junitxml=test_results_cli.xml"])
    elif output_format == "html":
        pytest_args.extend(["--html=test_report_cli.html", "--self-contained-html"])

    # Additional useful options
    pytest_args.extend(
        [
            "--tb=short",  # Short traceback format
            "--strict-markers",  # Strict marker checking
            "--disable-warnings",  # Disable warnings for cleaner output
        ]
    )

    print(f"Running CLI tests with arguments: {' '.join(pytest_args)}")

    # Run pytest
    return pytest.main(pytest_args)


def main():
    """Main entry point for CLI test runner."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive CLI tests for ai-trackdown-pytools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run all CLI tests
  %(prog)s --test-type options       # Run only option tests
  %(prog)s --test-type e2e --verbose # Run E2E tests with verbose output
  %(prog)s --coverage --parallel     # Run with coverage and parallel execution
  %(prog)s --marker cli --marker "not slow"  # Run CLI tests but skip slow tests
        """,
    )

    parser.add_argument(
        "--test-type",
        choices=["options", "interactive", "e2e", "formats", "errors", "all"],
        action="append",
        help="Types of tests to run (can be specified multiple times)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--coverage", "-c", action="store_true", help="Enable coverage reporting"
    )

    parser.add_argument(
        "--parallel", "-p", action="store_true", help="Run tests in parallel"
    )

    parser.add_argument(
        "--marker",
        "-m",
        action="append",
        help="Pytest markers to include/exclude (can be specified multiple times)",
    )

    parser.add_argument(
        "--output-format",
        choices=["text", "json", "xml", "html"],
        default="text",
        help="Output format for test results",
    )

    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List available tests without running them",
    )

    args = parser.parse_args()

    if args.list_tests:
        print("Available CLI test categories:")
        print("  options    - Test all CLI options and arguments")
        print("  interactive - Test interactive prompts and Rich UI")
        print("  e2e        - Test end-to-end ticket lifecycle workflows")
        print("  formats    - Test output formats (JSON, CSV, XML, YAML)")
        print("  errors     - Test error conditions and edge cases")
        print("  all        - Run all CLI tests")
        return 0

    # Run the tests
    exit_code = run_cli_tests(
        test_types=args.test_type,
        verbose=args.verbose,
        coverage=args.coverage,
        parallel=args.parallel,
        markers=args.marker,
        output_format=args.output_format,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
