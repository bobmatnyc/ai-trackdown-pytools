#!/usr/bin/env python3
"""Test runner for comprehensive edge case and error handling tests.

This script runs all edge case tests with appropriate configuration,
reporting, and filtering based on test categories and system capabilities.
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


def get_system_info() -> Dict[str, Any]:
    """Get system information for test configuration."""
    return {
        "platform": platform.system(),
        "python_version": sys.version_info,
        "architecture": platform.architecture()[0],
        "processor": platform.processor(),
        "total_memory": get_total_memory(),
        "available_disk": get_available_disk_space(),
    }


def get_total_memory() -> int:
    """Get total system memory in bytes."""
    try:
        import psutil

        return psutil.virtual_memory().total
    except ImportError:
        return 0


def get_available_disk_space() -> int:
    """Get available disk space in bytes."""
    try:
        import shutil

        return shutil.disk_usage("/").free
    except (ImportError, OSError):
        return 0


def check_dependencies() -> Dict[str, bool]:
    """Check availability of optional dependencies."""
    dependencies = {}

    # Check psutil for performance monitoring
    try:
        import psutil

        dependencies["psutil"] = True
    except ImportError:
        dependencies["psutil"] = False

    # Check GitPython for Git operations
    try:
        import git

        dependencies["gitpython"] = True
    except ImportError:
        dependencies["gitpython"] = False

    # Check asyncio for async tests
    try:
        import asyncio

        dependencies["asyncio"] = True
    except ImportError:
        dependencies["asyncio"] = False

    return dependencies


def get_test_categories() -> Dict[str, List[str]]:
    """Define test categories and their corresponding test files."""
    return {
        "boundary": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestBoundaryValues"
        ],
        "filesystem": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestFileSystemErrors"
        ],
        "malformed_data": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestMalformedData"
        ],
        "unicode": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestUnicodeAndInternationalization",
            "tests/unit/test_platform_and_i18n_edge_cases.py::TestUnicodeAndInternationalization",
        ],
        "concurrency": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestConcurrencyAndRaceConditions",
            "tests/unit/test_concurrency_and_performance_edge_cases.py::TestConcurrencyEdgeCases",
        ],
        "performance": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestResourceExhaustion",
            "tests/unit/test_concurrency_and_performance_edge_cases.py::TestResourceExhaustionScenarios",
            "tests/unit/test_concurrency_and_performance_edge_cases.py::TestStressConditions",
        ],
        "platform": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestPlatformSpecificEdgeCases",
            "tests/unit/test_platform_and_i18n_edge_cases.py::TestPlatformSpecificEdgeCases",
        ],
        "security": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestSecurityBoundaries",
            "tests/unit/test_security_edge_cases.py",
        ],
        "validation": [
            "tests/unit/test_edge_cases_and_error_handling.py::TestInputValidationEdgeCases",
            "tests/unit/test_edge_cases_and_error_handling.py::TestDataConsistencyEdgeCases",
        ],
        "regression": ["tests/unit/test_regression_prevention.py"],
        "encoding": [
            "tests/unit/test_platform_and_i18n_edge_cases.py::TestEncodingEdgeCases"
        ],
        "async": [
            "tests/unit/test_concurrency_and_performance_edge_cases.py::TestAsyncOperations"
        ],
    }


def build_pytest_args(
    categories: List[str],
    include_slow: bool,
    include_performance: bool,
    include_stress: bool,
    verbose: bool,
    output_dir: Path,
) -> List[str]:
    """Build pytest command arguments."""
    args = ["pytest"]

    # Add test paths based on categories
    test_categories = get_test_categories()
    test_paths = []

    if "all" in categories:
        # Add all edge case test files
        test_paths.extend(
            [
                "tests/unit/test_edge_cases_and_error_handling.py",
                "tests/unit/test_security_edge_cases.py",
                "tests/unit/test_concurrency_and_performance_edge_cases.py",
                "tests/unit/test_platform_and_i18n_edge_cases.py",
                "tests/unit/test_regression_prevention.py",
            ]
        )
    else:
        for category in categories:
            if category in test_categories:
                test_paths.extend(test_categories[category])

    args.extend(test_paths)

    # Verbosity
    if verbose:
        args.append("-v")
    else:
        args.append("-q")

    # Markers for test filtering
    markers = []

    if not include_slow:
        markers.append("not slow")

    if not include_performance:
        markers.append("not performance")

    if not include_stress:
        markers.append("not stress")

    # Platform-specific markers
    system = platform.system()
    if system == "Windows":
        markers.append("not linux and not macos")
    elif system == "Darwin":
        markers.append("not windows and not linux")
    elif system == "Linux":
        markers.append("not windows and not macos")

    if markers:
        args.extend(["-m", " and ".join(markers)])

    # Output configuration
    args.extend(
        [
            f"--junitxml={output_dir}/edge-case-results.xml",
            f"--html={output_dir}/edge-case-report.html",
            "--self-contained-html",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings",
        ]
    )

    # Coverage if requested
    if os.environ.get("ENABLE_COVERAGE"):
        args.extend(
            [
                "--cov=ai_trackdown_pytools",
                f"--cov-report=html:{output_dir}/coverage-html",
                f"--cov-report=xml:{output_dir}/coverage.xml",
                "--cov-report=term",
            ]
        )

    return args


def run_tests(
    categories: List[str],
    include_slow: bool = False,
    include_performance: bool = False,
    include_stress: bool = False,
    verbose: bool = False,
    output_dir: Path = None,
) -> int:
    """Run edge case tests with specified configuration."""

    if output_dir is None:
        output_dir = Path("test-reports") / f"edge-cases-{int(time.time())}"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get system information
    system_info = get_system_info()
    dependencies = check_dependencies()

    print("=== AI Trackdown PyTools Edge Case Test Runner ===")
    print(f"Platform: {system_info['platform']}")
    print(f"Python: {system_info['python_version']}")
    print(f"Memory: {system_info['total_memory'] // (1024**3)} GB")
    print(f"Test Categories: {', '.join(categories)}")
    print(f"Dependencies: {dependencies}")
    print(f"Output Directory: {output_dir}")
    print()

    # Set environment variables for test configuration
    os.environ["PYTEST_CURRENT_TEST"] = "edge_case_tests"

    # Skip certain tests based on system capabilities
    if system_info["total_memory"] < 2 * 1024**3:  # Less than 2GB
        os.environ["SKIP_MEMORY_INTENSIVE_TESTS"] = "1"
        print("⚠️  Skipping memory-intensive tests (insufficient RAM)")

    if system_info["available_disk"] < 1024**3:  # Less than 1GB
        os.environ["SKIP_LARGE_FILE_TESTS"] = "1"
        print("⚠️  Skipping large file tests (insufficient disk space)")

    if not dependencies["psutil"]:
        os.environ["SKIP_PERFORMANCE_MONITORING"] = "1"
        print("⚠️  Performance monitoring unavailable (psutil not installed)")

    if not dependencies["gitpython"]:
        os.environ["SKIP_GIT_TESTS"] = "1"
        print("⚠️  Git tests unavailable (GitPython not installed)")

    # Build pytest arguments
    pytest_args = build_pytest_args(
        categories,
        include_slow,
        include_performance,
        include_stress,
        verbose,
        output_dir,
    )

    print(f"Running: {' '.join(pytest_args)}")
    print("=" * 60)

    # Run tests
    start_time = time.time()
    result = subprocess.run(pytest_args, capture_output=False)
    end_time = time.time()

    # Generate summary
    duration = end_time - start_time
    print("\n" + "=" * 60)
    print(f"Edge case tests completed in {duration:.2f} seconds")
    print(f"Exit code: {result.returncode}")
    print(f"Reports generated in: {output_dir}")

    if result.returncode == 0:
        print("✅ All edge case tests passed!")
    else:
        print("❌ Some edge case tests failed. Check reports for details.")

    return result.returncode


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive edge case and error handling tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  boundary      - Boundary value testing (numeric limits, string lengths, etc.)
  filesystem    - File system error conditions and edge cases
  malformed_data - Corrupted YAML, invalid JSON, broken templates
  unicode       - Unicode and internationalization edge cases
  concurrency   - Multi-threading and race conditions
  performance   - Resource exhaustion and stress testing
  platform      - Platform-specific edge cases (Windows/macOS/Linux)
  security      - Security boundary testing and attack prevention
  validation    - Input validation and data consistency edge cases
  regression    - Regression prevention tests
  encoding      - Character encoding edge cases
  async         - Asynchronous operations testing
  all          - Run all edge case tests

Examples:
  python run_edge_case_tests.py --categories boundary validation
  python run_edge_case_tests.py --categories all --include-slow
  python run_edge_case_tests.py --categories security --verbose
  python run_edge_case_tests.py --categories performance --include-performance
        """,
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        default=["boundary", "filesystem", "validation"],
        help="Test categories to run (default: boundary, filesystem, validation)",
    )

    parser.add_argument(
        "--include-slow", action="store_true", help="Include slow-running tests"
    )

    parser.add_argument(
        "--include-performance",
        action="store_true",
        help="Include performance/stress tests",
    )

    parser.add_argument(
        "--include-stress",
        action="store_true",
        help="Include stress tests (may consume significant resources)",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose test output")

    parser.add_argument(
        "--output-dir", type=Path, help="Output directory for test reports"
    )

    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available test categories and exit",
    )

    args = parser.parse_args()

    if args.list_categories:
        print("Available test categories:")
        for category, tests in get_test_categories().items():
            print(f"  {category:12} - {len(tests)} test class(es)")
        return 0

    # Validate categories
    available_categories = list(get_test_categories().keys()) + ["all"]
    invalid_categories = [
        cat for cat in args.categories if cat not in available_categories
    ]

    if invalid_categories:
        print(f"Error: Invalid categories: {invalid_categories}")
        print(f"Available categories: {available_categories}")
        return 1

    # Run tests
    return run_tests(
        categories=args.categories,
        include_slow=args.include_slow,
        include_performance=args.include_performance,
        include_stress=args.include_stress,
        verbose=args.verbose,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
