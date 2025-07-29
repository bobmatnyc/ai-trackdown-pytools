#!/usr/bin/env python3
"""Test automation script with coverage reporting and comprehensive test execution."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class TestRunner:
    """Comprehensive test runner with coverage and reporting."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.src_dir = project_root / "src"
        self.coverage_dir = project_root / "htmlcov"
        self.reports_dir = project_root / "test-reports"

        # Ensure reports directory exists
        self.reports_dir.mkdir(exist_ok=True)

    def run_unit_tests(
        self, verbose: bool = False, coverage: bool = True
    ) -> Dict[str, Any]:
        """Run unit tests with optional coverage."""
        print("🧪 Running Unit Tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(self.tests_dir / "unit"),
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--junit-xml=" + str(self.reports_dir / "unit-tests.xml"),
        ]

        if coverage:
            cmd.extend(
                [
                    "--cov=" + str(self.src_dir / "ai_trackdown_pytools"),
                    "--cov-report=html:" + str(self.coverage_dir),
                    "--cov-report=xml:" + str(self.reports_dir / "coverage.xml"),
                    "--cov-report=term-missing",
                    "--cov-fail-under=70",  # Minimum 70% coverage
                ]
            )

        start_time = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )
        duration = time.time() - start_time

        return {
            "type": "unit",
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout,
            "errors": result.stderr,
            "command": " ".join(cmd),
        }

    def run_integration_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run integration tests."""
        print("🔗 Running Integration Tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(self.tests_dir / "integration"),
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--junit-xml=" + str(self.reports_dir / "integration-tests.xml"),
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )
        duration = time.time() - start_time

        return {
            "type": "integration",
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout,
            "errors": result.stderr,
            "command": " ".join(cmd),
        }

    def run_e2e_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run end-to-end tests."""
        print("🎯 Running End-to-End Tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(self.tests_dir / "e2e"),
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--junit-xml=" + str(self.reports_dir / "e2e-tests.xml"),
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )
        duration = time.time() - start_time

        return {
            "type": "e2e",
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout,
            "errors": result.stderr,
            "command": " ".join(cmd),
        }

    def run_validation_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run validation-specific tests."""
        print("✅ Running Validation Tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "validation",
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--junit-xml=" + str(self.reports_dir / "validation-tests.xml"),
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )
        duration = time.time() - start_time

        return {
            "type": "validation",
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout,
            "errors": result.stderr,
            "command": " ".join(cmd),
        }

    def run_cli_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run CLI-specific tests."""
        print("💻 Running CLI Tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "cli",
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--junit-xml=" + str(self.reports_dir / "cli-tests.xml"),
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )
        duration = time.time() - start_time

        return {
            "type": "cli",
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout,
            "errors": result.stderr,
            "command": " ".join(cmd),
        }

    def run_performance_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run performance tests."""
        print("⚡ Running Performance Tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "performance",
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--junit-xml=" + str(self.reports_dir / "performance-tests.xml"),
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )
        duration = time.time() - start_time

        return {
            "type": "performance",
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout,
            "errors": result.stderr,
            "command": " ".join(cmd),
        }

    def run_specific_tests(
        self, test_patterns: List[str], verbose: bool = False
    ) -> Dict[str, Any]:
        """Run specific tests by pattern."""
        print(f"🎯 Running Specific Tests: {', '.join(test_patterns)}")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "--junit-xml=" + str(self.reports_dir / "specific-tests.xml"),
        ]
        cmd.extend(test_patterns)

        start_time = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )
        duration = time.time() - start_time

        return {
            "type": "specific",
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout,
            "errors": result.stderr,
            "command": " ".join(cmd),
            "patterns": test_patterns,
        }

    def run_linting(self) -> Dict[str, Any]:
        """Run code linting."""
        print("🔍 Running Code Linting...")

        results = {}

        # Run ruff
        ruff_cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            str(self.src_dir),
            str(self.tests_dir),
        ]
        ruff_result = subprocess.run(
            ruff_cmd, capture_output=True, text=True, cwd=self.project_root
        )

        results["ruff"] = {
            "success": ruff_result.returncode == 0,
            "output": ruff_result.stdout,
            "errors": ruff_result.stderr,
        }

        # Run black check
        black_cmd = [
            sys.executable,
            "-m",
            "black",
            "--check",
            str(self.src_dir),
            str(self.tests_dir),
        ]
        black_result = subprocess.run(
            black_cmd, capture_output=True, text=True, cwd=self.project_root
        )

        results["black"] = {
            "success": black_result.returncode == 0,
            "output": black_result.stdout,
            "errors": black_result.stderr,
        }

        # Run mypy
        mypy_cmd = [sys.executable, "-m", "mypy", str(self.src_dir)]
        mypy_result = subprocess.run(
            mypy_cmd, capture_output=True, text=True, cwd=self.project_root
        )

        results["mypy"] = {
            "success": mypy_result.returncode == 0,
            "output": mypy_result.stdout,
            "errors": mypy_result.stderr,
        }

        overall_success = all(tool["success"] for tool in results.values())

        return {"type": "linting", "success": overall_success, "tools": results}

    def run_security_checks(self) -> Dict[str, Any]:
        """Run security checks."""
        print("🔒 Running Security Checks...")

        # Run safety check (if available)
        safety_cmd = [sys.executable, "-m", "safety", "check"]
        safety_result = subprocess.run(
            safety_cmd, capture_output=True, text=True, cwd=self.project_root
        )

        return {
            "type": "security",
            "success": safety_result.returncode == 0,
            "output": safety_result.stdout,
            "errors": safety_result.stderr,
        }

    def generate_test_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate comprehensive test report."""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "project": "ai-trackdown-pytools",
            "total_results": len(results),
            "successful_suites": sum(1 for r in results if r.get("success", False)),
            "failed_suites": sum(1 for r in results if not r.get("success", False)),
            "total_duration": sum(r.get("duration", 0) for r in results),
            "results": results,
        }

        # Save JSON report
        json_report_path = (
            self.reports_dir
            / f"test-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        with open(json_report_path, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        # Generate text summary
        summary = f"""
AI Trackdown PyTools - Test Report
=================================
Generated: {report_data['timestamp']}

SUMMARY:
--------
Total Test Suites: {report_data['total_results']}
Successful: {report_data['successful_suites']}
Failed: {report_data['failed_suites']}
Total Duration: {report_data['total_duration']:.2f}s

DETAILED RESULTS:
"""

        for result in results:
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            duration = result.get("duration", 0)
            summary += f"""
{status} {result['type'].upper()} ({duration:.2f}s)
{'-' * 50}
"""
            if not result.get("success", False) and result.get("errors"):
                summary += f"Errors: {result['errors'][:500]}...\n"

        summary += f"""
COVERAGE REPORT:
---------------
HTML Coverage Report: {self.coverage_dir}/index.html
XML Coverage Report: {self.reports_dir}/coverage.xml

ARTIFACTS:
----------
JSON Report: {json_report_path}
JUnit XML Files: {self.reports_dir}/*.xml
"""

        # Save text report
        text_report_path = (
            self.reports_dir
            / f"test-summary-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        )
        with open(text_report_path, "w") as f:
            f.write(summary)

        print(summary)
        return str(text_report_path)

    def clean_reports(self):
        """Clean old test reports and coverage data."""
        print("🧹 Cleaning old reports...")

        if self.reports_dir.exists():
            for file in self.reports_dir.glob("*"):
                if file.is_file():
                    file.unlink()

        if self.coverage_dir.exists():
            import shutil

            shutil.rmtree(self.coverage_dir)


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="AI Trackdown PyTools Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests"
    )
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument(
        "--validation", action="store_true", help="Run validation tests"
    )
    parser.add_argument("--cli", action="store_true", help="Run CLI tests")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests"
    )
    parser.add_argument("--lint", action="store_true", help="Run linting")
    parser.add_argument("--security", action="store_true", help="Run security checks")
    parser.add_argument("--all", action="store_true", help="Run all test suites")
    parser.add_argument(
        "--fast", action="store_true", help="Run fast test suite (unit + integration)"
    )
    parser.add_argument(
        "--no-coverage", action="store_true", help="Skip coverage reporting"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--clean", action="store_true", help="Clean reports before running"
    )
    parser.add_argument("--specific", nargs="+", help="Run specific test patterns")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    # Determine project root
    project_root = args.project_root
    if not (project_root / "pyproject.toml").exists():
        # Try to find project root
        current = Path.cwd()
        while current.parent != current:
            if (current / "pyproject.toml").exists():
                project_root = current
                break
            current = current.parent
        else:
            print("❌ Could not find project root (no pyproject.toml found)")
            sys.exit(1)

    runner = TestRunner(project_root)

    # Clean reports if requested
    if args.clean:
        runner.clean_reports()

    # Determine which tests to run
    results = []

    if args.specific:
        results.append(runner.run_specific_tests(args.specific, args.verbose))
    elif args.all:
        # Run all test suites
        if not args.no_coverage:
            results.append(runner.run_unit_tests(args.verbose, coverage=True))
        else:
            results.append(runner.run_unit_tests(args.verbose, coverage=False))
        results.append(runner.run_integration_tests(args.verbose))
        results.append(runner.run_e2e_tests(args.verbose))
        results.append(runner.run_validation_tests(args.verbose))
        results.append(runner.run_cli_tests(args.verbose))
        results.append(runner.run_performance_tests(args.verbose))
        if args.lint:
            results.append(runner.run_linting())
        if args.security:
            results.append(runner.run_security_checks())
    elif args.fast:
        # Run fast test suite
        results.append(
            runner.run_unit_tests(args.verbose, coverage=not args.no_coverage)
        )
        results.append(runner.run_integration_tests(args.verbose))
    else:
        # Run individual test suites as requested
        if args.unit:
            results.append(
                runner.run_unit_tests(args.verbose, coverage=not args.no_coverage)
            )
        if args.integration:
            results.append(runner.run_integration_tests(args.verbose))
        if args.e2e:
            results.append(runner.run_e2e_tests(args.verbose))
        if args.validation:
            results.append(runner.run_validation_tests(args.verbose))
        if args.cli:
            results.append(runner.run_cli_tests(args.verbose))
        if args.performance:
            results.append(runner.run_performance_tests(args.verbose))
        if args.lint:
            results.append(runner.run_linting())
        if args.security:
            results.append(runner.run_security_checks())

    # If no specific tests requested, run fast suite by default
    if not results:
        print("No specific tests requested, running fast test suite...")
        results.append(
            runner.run_unit_tests(args.verbose, coverage=not args.no_coverage)
        )
        results.append(runner.run_integration_tests(args.verbose))

    # Generate test report
    report_path = runner.generate_test_report(results)

    # Determine exit code
    failed_suites = [r for r in results if not r.get("success", False)]
    if failed_suites:
        print(f"\n❌ {len(failed_suites)} test suite(s) failed!")
        for failed in failed_suites:
            print(f"   - {failed['type']}")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} test suite(s) passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
